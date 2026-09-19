from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from alice_os.agent import RunManager
from alice_os.api import create_app
from alice_os.config import ConfigStore
from alice_os.memory import handle_memory_command, parse_memory_command
from alice_os.storage import Storage


def test_pending_cannot_replace_approved_until_review(storage):
    first = storage.add_global_memory("I prefer brief replies", category="preference", memory_key="style")
    proposed = storage.add_global_memory("I prefer detailed replies", category="preference", memory_key="style", source="agent")
    assert proposed["approved"] == 0
    assert [m["id"] for m in storage.context_memories("hello")] == [first["id"]]
    assert storage.search_global_memories("detailed") == []
    storage.update_global_memory(proposed["id"], content="I prefer moderately detailed replies")
    approved = storage.approve_global_memory(proposed["id"])
    assert approved["id"] == first["id"]
    assert len(storage.list_global_memories(include_pending=True)) == 1
    assert storage.context_memories("hello")[0]["content"] == "I prefer moderately detailed replies"


def test_forgetting_legacy_memory_survives_reopen(tmp_path):
    path = tmp_path / "memory.db"
    storage = Storage(path)
    session = storage.create_session()
    memory = storage.add_memory(session["id"], "Project: test migration")
    storage.close()
    storage = Storage(path)
    storage.delete_global_memory(memory["id"])
    storage.close()
    storage = Storage(path)
    assert storage.list_global_memories(include_pending=True) == []
    assert storage.search_memories(session["id"], "migration") == []
    storage.close()


@pytest.mark.parametrize("content", ["  ", "my password is test-secret", "API key: sk-123456789012345678901234", "account number 123456789", "4111 1111 1111 1111"])
def test_secrets_and_empty_values_rejected_on_every_write(storage, content):
    with pytest.raises(ValueError):
        storage.add_global_memory(content)
    memory = storage.add_global_memory("A harmless fact")
    with pytest.raises(ValueError):
        storage.update_global_memory(memory["id"], content=content)
    assert storage.list_global_memories()[0]["content"] == "A harmless fact"


def test_explicit_commands_are_precise_and_cross_session(storage):
    first, second = storage.create_session(), storage.create_session()
    assert "Remembered" in handle_memory_command(storage, "Hey Alice, remember project: Alice OS next step is voice tests", first["id"])
    assert "voice tests" in handle_memory_command(storage, "What were we working on?", second["id"])
    assert "voice tests" in handle_memory_command(storage, "Recall my projects", second["id"])
    assert "exact memory" in handle_memory_command(storage, "Forget voice", second["id"])
    assert len(storage.list_global_memories()) == 1
    assert "Forgot" in handle_memory_command(storage, "Forget Alice OS next step is voice tests.", second["id"])
    assert storage.list_global_memories() == []
    assert parse_memory_command('He said "remember my project"') is None
    assert parse_memory_command('"Forget my project"') is None
    assert "exact fact" in handle_memory_command(storage, "Remember that", second["id"])


@pytest.mark.asyncio
async def test_memory_commands_emit_normal_voice_events_without_provider(tmp_path, storage, monkeypatch):
    async def no_model(*args, **kwargs):
        raise AssertionError("Local commands must not call a model")
    monkeypatch.setattr("alice_os.agent.chat", no_model)
    manager = RunManager(storage, ConfigStore(tmp_path / "config"))
    session = storage.create_session()
    run = manager.start(session_id=session["id"], user_message="Remember that I prefer concise answers", provider_id="", model="", agent_mode=False)
    await run.task
    assert run.terminal
    assert [event.name for event in run.events] == ["token", "message", "done"]
    assert "Remembered" in storage.list_messages(session["id"])[-1].content
    assert storage.context_memories("hello")[0]["category"] == "preference"


def test_memory_api_auth_review_and_validation(tmp_path: Path):
    app = create_app(tmp_path / "data")
    with TestClient(app) as client:
        assert client.get("/api/memories").status_code == 401
        assert client.post("/api/memories/nope/approve").status_code == 401
        client.get("/")
        pending = app.state.storage.add_global_memory("A proposed project", category="project", source="agent")
        assert client.get("/api/memories").json()["memories"][0]["approved"] == 0
        assert client.post(f"/api/memories/{pending['id']}/approve").status_code == 200
        assert client.post(f"/api/memories/{pending['id']}/approve").status_code == 404
        approved = client.get("/api/memories").json()["memories"][0]
        assert approved["approved"] == 1
        client.delete(f"/api/memories/{approved['id']}")
        assert client.post("/api/memories", json={"content": "my password is nope"}).status_code == 400
        created = client.post("/api/memories", json={"content": "Next step: voice testing", "category": "project"}).json()
        assert created["approved"] == 1
        assert client.patch(f"/api/memories/{created['id']}", json={"content": "Next step: UI testing"}).status_code == 200
        assert client.get("/api/memories").json()["memories"][0]["content"] == "Next step: UI testing"
        assert client.delete(f"/api/memories/{created['id']}").status_code == 200
        assert client.get("/api/memories").json()["memories"] == []
        session = client.post("/api/sessions", json={"workspace": str(tmp_path)}).json()
        response = client.post("/api/runs", json={"session_id": session["id"], "message": "Recall memories", "provider_id": "", "model": "", "agent_mode": False})
        assert response.status_code == 200
