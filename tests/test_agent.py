from __future__ import annotations

import re
from pathlib import Path

import pytest

from alice_os.agent import RunManager


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
