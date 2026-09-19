import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from alice_os.agent import AgentRun, RunManager
from alice_os.api import create_app
from alice_os.config import ConfigStore
from alice_os.models import AssistantTurn, ToolCall
from alice_os.skill_packages import TEMPLATES, PackageStore, SkillManifest
from alice_os.skills import AgentSkill, SkillStore
from alice_os.storage import Storage
from alice_os.tools import ToolRegistry


def test_package_roundtrip_permissions_and_updates(tmp_path):
    store = SkillStore(tmp_path)
    manifest = TEMPLATES[0]
    assert not store.install_package(manifest)["enabled"]
    with pytest.raises(ValueError, match="disabled"):
        store.get(manifest.id)
    store.packages.set_enabled(manifest.id, True)
    restored = SkillStore(tmp_path)
    skill = restored.get(manifest.id)
    assert skill.allowed_tools == tuple(manifest.tools)
    assert restored.packages.export(manifest.id) == manifest.model_dump()
    assert {entry["function"]["name"] for entry in ToolRegistry().definitions(
        read_only=skill.read_only, allowed_tools=skill.allowed_tools)} == set(manifest.tools)
    assert not restored.install_package(manifest)["enabled"]
    with pytest.raises(ValueError, match="cannot be replaced"):
        restored.upsert(AgentSkill(manifest.id, "Test", "Test", "Test"))


@pytest.mark.parametrize("changes", [{"id": "../escape"}, {"entrypoint": "evil.py"},
                                      {"tools": ["workspace_read", "workspace_read"]},
                                      {"instructions": "  "}, {"schema_version": 2}])
def test_manifest_rejects_invalid_or_executable_fields(changes):
    with pytest.raises(ValidationError):
        SkillManifest.model_validate({**TEMPLATES[0].model_dump(), **changes})


@pytest.mark.parametrize("tools", [["unknown_tool"], ["process_run"], ["memory_store"]])
def test_unhealthy_packages_cannot_enable(tmp_path, tools):
    store = PackageStore(tmp_path)
    manifest = SkillManifest.model_validate({**TEMPLATES[0].model_dump(), "tools": tools})
    assert store.install(manifest)["issues"]
    with pytest.raises(ValueError):
        store.set_enabled(manifest.id, True)


def test_missing_dependency_and_corrupt_catalog(tmp_path, monkeypatch):
    monkeypatch.setattr("alice_os.skill_packages.shutil.which", lambda _: None)
    store = PackageStore(tmp_path)
    store.install(TEMPLATES[1])
    with pytest.raises(ValueError, match="git"):
        store.set_enabled(TEMPLATES[1].id, True)
    store.path.write_text("broken", encoding="utf-8")
    broken = PackageStore(tmp_path)
    assert broken.load_error
    with pytest.raises(ValueError, match="Repair"):
        broken.install(TEMPLATES[0])
    assert store.path.read_text() == "broken"


def test_failed_persistence_does_not_leave_permission_changes_in_memory(tmp_path, monkeypatch):
    store = PackageStore(tmp_path)
    store.install(TEMPLATES[0])

    def fail():
        raise OSError("Disk full")

    monkeypatch.setattr(store, "_save", fail)
    with pytest.raises(OSError):
        store.set_enabled(TEMPLATES[0].id, True)
    assert not store.get(TEMPLATES[0].id)["enabled"]
    with pytest.raises(OSError):
        store.delete(TEMPLATES[0].id)
    assert store.get(TEMPLATES[0].id) is not None


def test_api_package_lifecycle_and_authentication(tmp_path):
    app = create_app(tmp_path / "data")
    with TestClient(app) as client:
        assert client.get("/api/skill-packages").status_code == 401
        assert client.post("/api/skill-packages", json=TEMPLATES[0].model_dump()).status_code == 401
        client.get("/")
        manifest = client.get("/api/skill-packages").json()["templates"][0]
        assert client.post("/api/skill-packages", json=manifest).status_code == 200
        path = "/api/skill-packages/" + manifest["id"]
        assert not client.get("/api/skills").json()["skills"][-1]["available"]
        assert client.patch(path, json={"enabled": True}).json()["package"]["available"]
        assert client.get(path + "/manifest").json() == manifest
        assert client.post("/api/skill-packages", json={**manifest, "id": "general"}).status_code == 400
        assert client.post("/api/skill-packages", json={**manifest, "script": "bad"}).status_code == 422
        assert client.patch(path, json={"enabled": "false"}).status_code == 422
        assert client.delete(path).status_code == 204
        assert client.get(path + "/manifest").status_code == 404


@pytest.fixture
def manager(tmp_path):
    config = ConfigStore(tmp_path / "data")
    storage = Storage(config.data_dir / "alice.db")
    yield RunManager(storage, config)
    storage.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("fallback", [False, True])
async def test_agent_enforces_package_allowlist_even_for_hallucinated_calls(manager, tmp_path, monkeypatch, fallback):
    manager.skills.install_package(TEMPLATES[0])
    manager.skills.packages.set_enabled(TEMPLATES[0].id, True)
    session = manager.storage.create_session(workspace=str(tmp_path))
    invocations = []

    async def infer(*args, **kwargs):
        invocations.append(kwargs)
        if len(invocations) == 1 and fallback:
            from alice_os.providers import ToolsUnsupportedError
            raise ToolsUnsupportedError("Unsupported")
        if len(invocations) == (2 if fallback else 1):
            call = ToolCall(id="blocked", name="workspace_write", arguments={"path": "oops.txt", "content": "bad"})
            return AssistantTurn(content=json.dumps({"tool": call.name, "arguments": call.arguments})) if fallback else AssistantTurn(content="", tool_calls=[call])
        return AssistantTurn(content="Cannot write with this skill.")

    monkeypatch.setattr("alice_os.agent.chat", infer)
    run = manager.start(session_id=session["id"], user_message="Write a file", provider_id=manager.config.get().providers[0].id,
                        model="test", agent_mode=True, skill_id=TEMPLATES[0].id)
    await asyncio.wait_for(run.task, 5)
    assert not (tmp_path / "oops.txt").exists()
    assert not run.approval_futures
    assert any("not permitted" in message.content for message in manager.storage.list_messages(session["id"]))
    assert {tool["function"]["name"] for tool in invocations[0]["tools"]} == set(TEMPLATES[0].tools)


@pytest.mark.asyncio
async def test_disabling_package_while_approval_pending_blocks_execution(manager, tmp_path):
    manifest = SkillManifest.model_validate({**TEMPLATES[0].model_dump(), "read_only": False, "tools": ["workspace_write"]})
    manager.skills.install_package(manifest)
    manager.skills.packages.set_enabled(manifest.id, True)
    skill = manager.skills.get(manifest.id)
    session = manager.storage.create_session(workspace=str(tmp_path))
    run = AgentRun(id="test", session_id=session["id"])
    call = ToolCall(id="write", name="workspace_write", arguments={"path": "blocked.txt", "content": "no"})
    task = asyncio.create_task(manager._execute_tool(run, call, tmp_path, "test", skill=skill))
    try:
        async with asyncio.timeout(5):
            while "write" not in run.approval_futures:
                await asyncio.sleep(0.01)
        manager.skills.packages.set_enabled(manifest.id, False)
        run.approval_futures["write"].set_result(True)
        result = json.loads(await task)
        assert "disabled" in result["error"]
        assert not (tmp_path / "blocked.txt").exists()
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def test_deleted_or_disabled_skill_does_not_fall_back_to_general(manager, tmp_path):
    session = manager.storage.create_session(workspace=str(tmp_path))
    with pytest.raises(ValueError, match="Unknown skill"):
        manager.start(session_id=session["id"], user_message="Hello", provider_id="test", model="test", agent_mode=True, skill_id="deleted-package")


@pytest.mark.asyncio
async def test_allowed_native_tool_runs_but_empty_allowlist_exposes_nothing(manager, tmp_path):
    (tmp_path / "hello.txt").write_text("hello", encoding="utf-8")
    manager.skills.install_package(TEMPLATES[0])
    manager.skills.packages.set_enabled(TEMPLATES[0].id, True)
    skill = manager.skills.get(TEMPLATES[0].id)
    session = manager.storage.create_session(workspace=str(tmp_path))
    run = AgentRun(id="read", session_id=session["id"])
    call = ToolCall(id="read", name="workspace_read", arguments={"path": "hello.txt"})
    result = json.loads(await manager._execute_tool(run, call, tmp_path, "read", skill=skill, read_only=True))
    assert result["content"].endswith(" | hello")
    empty = SkillManifest.model_validate({**TEMPLATES[0].model_dump(), "tools": []})
    manager.skills.install_package(empty)
    manager.skills.packages.set_enabled(empty.id, True)
    skill = manager.skills.get(empty.id)
    assert manager.tools.definitions(allowed_tools=skill.allowed_tools) == []
    denied = json.loads(await manager._execute_tool(run, call, tmp_path, "read", skill=skill, read_only=True))
    assert "not permitted" in denied["error"]
