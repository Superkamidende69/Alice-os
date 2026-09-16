from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path

import pytest

from alice_os.agent import MAX_RUN_EVENTS, AgentRun, RunCapacityError, RunConflictError, RunManager
from alice_os.config import ConfigStore
from alice_os.models import AssistantTurn, ToolCall
from alice_os.storage import Storage


@pytest.mark.parametrize(
    ("content", "expected_name", "expected_arguments"),
    [
        (
            '{"tool":"workspace_read","arguments":{"path":"README.md"}}',
            "workspace_read",
            {"path": "README.md"},
        ),
        (
            '```json\n{"tool":"workspace_search","arguments":{"query":"Alice"}}\n```',
            "workspace_search",
            {"query": "Alice"},
        ),
        ('{"tool":"workspace_list"}', "workspace_list", {}),
    ],
)
def test_fallback_tool_parser_accepts_exact_json_envelopes(
    content: str, expected_name: str, expected_arguments: dict[str, object]
) -> None:
    call = RunManager._parse_fallback_tool(content)

    assert call is not None
    assert call.id.startswith("call_")
    assert call.name == expected_name
    assert call.arguments == expected_arguments


@pytest.mark.parametrize(
    "content",
    [
        'I will use a tool: {"tool":"workspace_list"}',
        "[]",
        "{}",
        '{"tool":"workspace_read","arguments":["README.md"]}',
        "```json\nnot json\n```",
    ],
)
def test_fallback_tool_parser_rejects_ambiguous_or_invalid_payloads(
    content: str,
) -> None:
    assert RunManager._parse_fallback_tool(content) is None


def test_approval_fingerprint_is_stable_and_binds_the_full_request(
    tmp_path: Path,
) -> None:
    workspace = (tmp_path / "workspace").resolve()
    other_workspace = (tmp_path / "other-workspace").resolve()

    first = RunManager._fingerprint(
        "workspace_write",
        {"content": "héllo", "path": "notes.txt", "options": {"b": 2, "a": 1}},
        workspace,
    )
    reordered = RunManager._fingerprint(
        "workspace_write",
        {"options": {"a": 1, "b": 2}, "path": "notes.txt", "content": "héllo"},
        workspace,
    )

    assert first == reordered
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert first != RunManager._fingerprint(
        "workspace_write",
        {"content": "changed", "path": "notes.txt", "options": {"a": 1, "b": 2}},
        workspace,
    )
    assert first != RunManager._fingerprint(
        "process_run",
        {"content": "héllo", "path": "notes.txt", "options": {"a": 1, "b": 2}},
        workspace,
    )
    assert first != RunManager._fingerprint(
        "workspace_write",
        {"content": "héllo", "path": "notes.txt", "options": {"a": 1, "b": 2}},
        other_workspace,
    )


@pytest.fixture
def manager(tmp_path: Path):
    config = ConfigStore(tmp_path / "data")
    storage = Storage(config.data_dir / "alice.db")
    manager = RunManager(storage, config)
    yield manager
    storage.close()


@pytest.mark.parametrize("depth,expected", [("quick", "brief, direct"), ("thorough", "thorough answer"), ("balanced", None)])
async def test_response_depth_reaches_provider(manager, tmp_path, monkeypatch, depth, expected):
    captured = []
    async def infer(*args, **kwargs):
        captured.append(kwargs["messages"][0]["content"])
        return AssistantTurn(content="Hello")
    monkeypatch.setattr("alice_os.agent.chat", infer)
    session = manager.storage.create_session(workspace=str(tmp_path))
    run = manager.start(session_id=session["id"], user_message="Hello", provider_id="ollama",
                        model="test-model", agent_mode=False, response_depth=depth)
    await run.task
    assert captured
    if expected:
        assert expected in captured[0]
    else:
        assert "Response depth preference" not in captured[0]


def start_run(manager: RunManager, tmp_path: Path, *, session_id: str = "", skill_id: str = "general") -> AgentRun:
    session_id = session_id or manager.storage.create_session(workspace=str(tmp_path))["id"]
    return manager.start(session_id=session_id, user_message="Hello", provider_id="ollama",
                         model="test-model", agent_mode=True, skill_id=skill_id)


async def test_replay_retention_keeps_monotonic_ids_and_reports_a_gap() -> None:
    run = AgentRun(id="run", session_id="session")
    for index in range(MAX_RUN_EVENTS + 5):
        await run.emit("token", text=str(index))
    await run.emit("done", status="completed")

    assert len(run.events) == MAX_RUN_EVENTS
    replay = [event async for event in run.stream()]
    assert replay[0].name == "history_gap"
    assert replay[0].data["session_id"] == "session"
    assert replay[-1].sequence == MAX_RUN_EVENTS + 6
    assert replay[-1].name == "done"
    tail = [event async for event in run.stream(after=run.sequence - 1)]
    assert [event.name for event in tail] == ["done"]
    assert [event async for event in run.stream(after=run.sequence)] == []


async def test_cancellation_before_task_starts_terminates_stream(manager, tmp_path: Path) -> None:
    run = start_run(manager, tmp_path)
    await manager.cancel(run.id)
    assert run.task.done()
    assert run.terminal
    assert [event.name async for event in run.stream()] == ["cancelled"]
    assert manager.storage.list_messages(run.session_id) == []


async def test_duplicate_and_excess_runs_are_rejected_without_orphans(manager, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("alice_os.agent.MAX_ACTIVE_RUNS", 1)
    run = start_run(manager, tmp_path)
    try:
        with pytest.raises(RunConflictError):
            start_run(manager, tmp_path, session_id=run.session_id)
        with pytest.raises(RunCapacityError):
            start_run(manager, tmp_path)
        assert list(manager.runs) == [run.id]
    finally:
        await manager.shutdown()


async def test_unknown_provider_does_not_leave_a_run(manager, tmp_path: Path) -> None:
    session = manager.storage.create_session(workspace=str(tmp_path))
    with pytest.raises(KeyError):
        manager.start(session_id=session["id"], user_message="Hello", provider_id="missing-provider",
                      model="test-model", agent_mode=True)
    assert manager.runs == {}


async def test_shutdown_cancels_pending_approval_and_allows_no_new_runs(manager, tmp_path: Path, monkeypatch) -> None:
    async def infer(*args, **kwargs):
        return AssistantTurn(tool_calls=[ToolCall(id="write", name="workspace_write", arguments={"path": "notes.txt", "content": "test"})])

    monkeypatch.setattr("alice_os.agent.chat", infer)
    run = start_run(manager, tmp_path)
    async with asyncio.timeout(2):
        async for event in run.stream():
            if event.name == "approval_required":
                break
    assert run.approval_futures
    await manager.shutdown()
    assert run.terminal and run.task.done()
    assert run.events[-1].name == "cancelled"
    assert not run.approval_futures
    assert not (tmp_path / "notes.txt").exists()
    with pytest.raises(RunCapacityError):
        start_run(manager, tmp_path)


async def test_run_retention_never_evicts_active_work(manager, monkeypatch) -> None:
    monkeypatch.setattr("alice_os.agent.MAX_RETAINED_RUNS", 2)
    active = AgentRun(id="active", session_id="active-session")
    manager.runs[active.id] = active
    for index in range(4):
        run = AgentRun(id=str(index), session_id=str(index))
        await run.emit("done")
        manager.runs[run.id] = run
    manager.prune()
    assert list(manager.runs) == ["active", "3"]
    manager.runs["3"].finished_at = time.monotonic() - 3600
    manager.prune()
    assert list(manager.runs) == ["active"]
