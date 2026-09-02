from __future__ import annotations

from pathlib import Path

import pytest

from alice_os.storage import Storage


def test_sessions_messages_and_memories_persist_across_reopen(tmp_path: Path) -> None:
    database = tmp_path / "alice-data" / "alice.db"
    first = Storage(database)
    try:
        session = first.create_session(
            title="  Persistent conversation  ",
            workspace=str(tmp_path),
            provider_id="local",
            model="example-model",
        )
        user = first.add_message(
            session["id"],
            "user",
            "Remember this",
            {"source": "test", "nested": {"value": 3}},
        )
        assistant = first.add_message(session["id"], "assistant", "I will")
        memory = first.add_memory(session["id"], "The preferred colour is blue")
    finally:
        first.close()

    reopened = Storage(database)
    try:
        loaded = reopened.get_session(session["id"])
        assert loaded["title"] == "Persistent conversation"
        assert loaded["workspace"] == str(tmp_path)
        assert loaded["provider_id"] == "local"
        assert loaded["model"] == "example-model"
        assert [message["id"] for message in loaded["messages"]] == [
            user.id,
            assistant.id,
        ]
        assert loaded["messages"][0]["metadata"] == {
            "source": "test",
            "nested": {"value": 3},
        }
        assert loaded["messages"][1]["metadata"] == {}

        matches = reopened.search_memories(session["id"], "BLUE")
        assert matches == [
            {
                "id": memory["id"],
                "content": "The preferred colour is blue",
                "created_at": memory["created_at"],
            }
        ]
    finally:
        reopened.close()


def test_update_and_delete_session_cascades_related_records(storage: Storage) -> None:
    session = storage.create_session(title="Before")
    storage.add_message(session["id"], "user", "hello")
    storage.add_memory(session["id"], "durable fact")

    updated = storage.update_session(
        session["id"], title="After", model="new-model", ignored="not stored"
    )
    assert updated["title"] == "After"
    assert updated["model"] == "new-model"
    assert "ignored" not in updated

    storage.delete_session(session["id"])

    with pytest.raises(KeyError, match="Unknown session"):
        storage.get_session(session["id"])
    assert storage.list_messages(session["id"]) == []
    assert storage.search_memories(session["id"], "fact") == []


def test_unknown_session_mutations_raise(storage: Storage) -> None:
    with pytest.raises(KeyError, match="Unknown session"):
        storage.update_session("missing", title="Nope")
    with pytest.raises(KeyError, match="Unknown session"):
        storage.delete_session("missing")
