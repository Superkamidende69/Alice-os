from __future__ import annotations

from pathlib import Path

import pytest

from alice_os.storage import Storage
from alice_os.tools import ToolContext


@pytest.fixture
def storage(tmp_path: Path):
    store = Storage(tmp_path / "data" / "alice.db")
    try:
        yield store
    finally:
        store.close()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    path = tmp_path / "workspace"
    path.mkdir()
    return path


@pytest.fixture
def tool_context(storage: Storage, workspace: Path) -> ToolContext:
    session = storage.create_session(workspace=str(workspace))
    return ToolContext(
        workspace=workspace,
        session_id=session["id"],
        storage=storage,
    )
