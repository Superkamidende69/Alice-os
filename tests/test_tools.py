from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from alice_os.tools import (
    ToolContext,
    ToolError,
    _docker_run_argv,
    git_diff,
    git_status,
    git_worktree_create,
    git_worktree_create_preview,
    resolve_workspace_path,
    sandbox_process_run_preview,
    workspace_patch,
    workspace_patch_preview,
    workspace_read,
    workspace_search,
    workspace_write,
    workspace_write_preview,
)


def test_path_resolution_confines_relative_and_absolute_paths(
    tool_context: ToolContext, workspace: Path, tmp_path: Path
) -> None:
    inside = workspace / "inside.txt"
    inside.write_text("inside", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    assert resolve_workspace_path(tool_context, "inside.txt", must_exist=True) == inside.resolve()

    for escaping_path, must_exist in (
        ("../outside.txt", True),
        (str(outside.resolve()), True),
        ("nested/../../new-outside.txt", False),
    ):
        with pytest.raises(ToolError, match="escapes the selected workspace"):
            resolve_workspace_path(tool_context, escaping_path, must_exist=must_exist)


def test_path_resolution_rejects_symlink_escape(
    tool_context: ToolContext, workspace: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside-directory"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = workspace / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        if os.name != "nt":
            pytest.skip(f"This host cannot create directory symlinks: {error}")
        junction = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        if junction.returncode != 0:
            pytest.skip(
                "This host can create neither a directory symlink nor junction: "
                f"{junction.stderr.strip() or junction.stdout.strip()}"
            )

    with pytest.raises(ToolError, match="escapes the selected workspace"):
        resolve_workspace_path(tool_context, "escape/secret.txt", must_exist=True)


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific path syntax")
def test_path_resolution_rejects_relative_alternate_data_stream(
    tool_context: ToolContext,
) -> None:
    with pytest.raises(ToolError, match="alternate data stream"):
        resolve_workspace_path(tool_context, "file.txt:secret", must_exist=False)


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific path syntax")
def test_path_resolution_rejects_absolute_alternate_data_stream(
    tool_context: ToolContext, workspace: Path
) -> None:
    ads_path = f"{workspace / 'file.txt'}:secret"
    with pytest.raises(ToolError, match="alternate data stream"):
        resolve_workspace_path(tool_context, ads_path, must_exist=False)


@pytest.mark.asyncio
async def test_workspace_write_preview_write_and_bounded_read(
    tool_context: ToolContext, workspace: Path
) -> None:
    target = workspace / "notes" / "example.txt"
    target.parent.mkdir()
    target.write_text("old first\nold second\n", encoding="utf-8")
    replacement = "new first\nnew second\nnew third\n"

    preview = workspace_write_preview(
        tool_context, {"path": "notes/example.txt", "content": replacement}
    )
    assert preview["summary"] == "Write notes/example.txt"
    assert "-old first" in preview["diff"]
    assert "+new third" in preview["diff"]
    assert preview["truncated"] is False

    written = await workspace_write(
        tool_context, {"path": "notes/example.txt", "content": replacement}
    )
    assert written == {
        "path": "notes/example.txt",
        "bytes_written": len(replacement.encode("utf-8")),
    }
    assert target.read_text(encoding="utf-8") == replacement

    result = await workspace_read(
        tool_context,
        {"path": "notes/example.txt", "start_line": 2, "end_line": 3},
    )
    assert result["path"] == "notes/example.txt"
    assert result["start_line"] == 2
    assert result["end_line"] == 3
    assert result["total_lines"] == 3
    assert result["content"] == "     2 | new second\n     3 | new third"
    assert len(result["sha256"]) == 64
    assert result["trust"] == "untrusted_workspace_data"


@pytest.mark.asyncio
async def test_workspace_patch_is_review_bound_and_atomic(
    tool_context: ToolContext, workspace: Path
) -> None:
    target = workspace / "src" / "example.py"
    target.parent.mkdir()
    target.write_text("first = 1\nsecond = 2\n", encoding="utf-8")
    snapshot = await workspace_read(tool_context, {"path": "src/example.py"})
    arguments = {
        "path": "src/example.py",
        "old_text": "second = 2",
        "new_text": "second = first + 1",
        "expected_sha256": snapshot["sha256"],
    }

    preview = workspace_patch_preview(tool_context, arguments)
    assert preview["summary"] == "Patch src/example.py"
    assert "-second = 2" in preview["diff"]
    assert "+second = first + 1" in preview["diff"]

    result = await workspace_patch(tool_context, arguments)
    assert result["path"] == "src/example.py"
    assert target.read_text(encoding="utf-8") == "first = 1\nsecond = first + 1\n"


@pytest.mark.asyncio
async def test_workspace_patch_rejects_stale_or_ambiguous_requests(
    tool_context: ToolContext, workspace: Path
) -> None:
    target = workspace / "example.txt"
    target.write_text("same\nsame\n", encoding="utf-8")
    snapshot = await workspace_read(tool_context, {"path": "example.txt"})

    with pytest.raises(ToolError, match="exactly once"):
        workspace_patch_preview(
            tool_context,
            {
                "path": "example.txt",
                "old_text": "same",
                "new_text": "different",
                "expected_sha256": snapshot["sha256"],
            },
        )

    target.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ToolError, match="changed since it was read"):
        await workspace_patch(
            tool_context,
            {
                "path": "example.txt",
                "old_text": "changed",
                "new_text": "new",
                "expected_sha256": snapshot["sha256"],
            },
        )


@pytest.mark.asyncio
async def test_git_tools_report_working_tree_changes(
    tool_context: ToolContext, workspace: Path
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.email", "alice@example.test"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "Alice Test"], cwd=workspace, check=True)
    target = workspace / "example.txt"
    target.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "example.txt"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=workspace, check=True)
    target.write_text("after\n", encoding="utf-8")

    status = await git_status(tool_context, {})
    assert status["branch"]
    assert status["changes"] == [{"status": " M", "path": "example.txt"}]

    diff = await git_diff(tool_context, {"path": "example.txt"})
    assert "-before" in diff["diff"]
    assert "+after" in diff["diff"]

    with pytest.raises(ToolError, match="must stay inside"):
        await git_diff(tool_context, {"path": "../outside.txt"})


@pytest.mark.asyncio
async def test_git_worktree_create_isolates_and_switches_the_session(
    tool_context: ToolContext, workspace: Path
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.email", "alice@example.test"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "Alice Test"], cwd=workspace, check=True)
    (workspace / "example.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "example.txt"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=workspace, check=True)

    arguments = {"branch": "alice/add-worktree-support"}
    preview = git_worktree_create_preview(tool_context, arguments)
    assert preview["source_workspace"] == str(workspace.resolve())
    assert preview["branch"] == "alice/add-worktree-support"

    result = await git_worktree_create(tool_context, arguments)
    isolated = Path(result["workspace"])
    assert isolated.is_dir()
    assert (isolated / "example.txt").read_text(encoding="utf-8") == "base\n"
    assert tool_context.storage.get_session(tool_context.session_id)["workspace"] == str(isolated)
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=isolated, check=True, capture_output=True, text=True
    )
    assert branch.stdout.strip() == "alice/add-worktree-support"

    with pytest.raises(ToolError, match="already exists"):
        await git_worktree_create(tool_context, arguments)


def test_sandbox_preview_and_command_disable_network_and_limit_mounts(
    tool_context: ToolContext, workspace: Path
) -> None:
    arguments = {
        "argv": ["python", "-m", "pytest", "-q"],
        "image": "python:3.13-slim",
        "cwd": ".",
    }
    preview = sandbox_process_run_preview(tool_context, arguments)
    assert preview["network"] == "disabled"
    assert preview["workspace_access"] == "read-only"
    command = _docker_run_argv(
        tool_context, arguments["argv"], workspace, arguments["image"], True
    )
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert any(item.endswith(",readonly") for item in command if item.startswith("--mount="))


def test_sandbox_preview_rejects_unsafe_image_name(tool_context: ToolContext) -> None:
    with pytest.raises(ToolError, match="safe, locally available"):
        sandbox_process_run_preview(
            tool_context,
            {"argv": ["echo", "no"], "image": "--privileged"},
        )


@pytest.mark.asyncio
async def test_workspace_search_honours_glob_case_limit_and_skipped_directories(
    tool_context: ToolContext, workspace: Path
) -> None:
    source = workspace / "src"
    source.mkdir()
    (source / "first.py").write_text(
        "nothing here\nNeedle appears here\nneedle again\n", encoding="utf-8"
    )
    (source / "second.txt").write_text("needle in text", encoding="utf-8")
    ignored = workspace / ".git"
    ignored.mkdir()
    (ignored / "ignored.py").write_text("needle", encoding="utf-8")

    result = await workspace_search(
        tool_context,
        {"query": "needle", "glob": "*.py", "case_sensitive": False},
    )
    assert [(item["path"], item["line"]) for item in result["matches"]] == [
        ("src/first.py", 2),
        ("src/first.py", 3),
    ]
    assert result["trust"] == "untrusted_workspace_data"
    assert result["truncated"] is False

    case_sensitive = await workspace_search(
        tool_context,
        {
            "query": "needle",
            "glob": "*.py",
            "case_sensitive": True,
            "limit": 1,
        },
    )
    assert case_sensitive["matches"] == [
        {"path": "src/first.py", "line": 3, "text": "needle again"}
    ]
    assert case_sensitive["truncated"] is False


@pytest.mark.asyncio
async def test_workspace_operations_reject_outside_targets(
    tool_context: ToolContext, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("do not read", encoding="utf-8")

    with pytest.raises(ToolError, match="escapes the selected workspace"):
        await workspace_read(tool_context, {"path": str(outside)})
    with pytest.raises(ToolError, match="escapes the selected workspace"):
        await workspace_write(tool_context, {"path": "../created.txt", "content": "blocked"})
    with pytest.raises(ToolError, match="escapes the selected workspace"):
        await workspace_search(tool_context, {"path": str(tmp_path), "query": "anything"})
