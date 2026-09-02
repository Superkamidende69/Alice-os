from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from alice_os.api import create_app


def test_api_requires_session_token_and_rejects_foreign_origin(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    app = create_app(tmp_path / "data")

    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        unauthorized = client.post("/api/sessions", json={"workspace": str(workspace)})
        assert unauthorized.status_code == 401

        index = client.get("/")
        assert index.status_code == 200
        cookie = index.headers["set-cookie"].lower()
        assert "alice_session=" in cookie
        assert "httponly" in cookie
        assert "samesite=strict" in cookie

        skills = client.get("/api/skills")
        assert skills.status_code == 200
        assert [skill["id"] for skill in skills.json()["skills"]] == [
            "general",
            "plan",
            "debug",
            "review",
            "implement",
        ]

        authenticated = client.post("/api/sessions", json={"workspace": str(workspace)})
        assert authenticated.status_code == 200

        rejected_origin = client.get(
            f"/api/sessions/{authenticated.json()['id']}",
            headers={"Origin": "https://attacker.example"},
        )
        assert rejected_origin.status_code == 403


def test_voice_status_is_session_protected(tmp_path: Path) -> None:
    app = create_app(tmp_path / "data")
    with TestClient(app) as client:
        assert client.get("/api/voice/status").status_code == 401
        client.get("/")
        response = client.get("/api/voice/status")
        assert response.status_code == 200
        assert isinstance(response.json()["ready"], bool)


def test_voice_reference_upload_stays_in_alice_data(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    app = create_app(data_dir)
    with TestClient(app) as client:
        headers = {"X-Alice-Token": app.state.session_token}
        uploaded = client.post(
            "/api/voice/references",
            headers=headers,
            files={"reference": ("allowed-voice.wav", b"RIFFdemo", "audio/wav")},
        )
        assert uploaded.status_code == 200
        name = uploaded.json()["name"]
        assert (data_dir / "voice" / "references" / name).is_file()

        listed = client.get("/api/voice/references", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["references"][0]["name"] == name
        assert listed.json()["references"][0]["label"] == "allowed voice"

        removed = client.delete(f"/api/voice/references/{name}", headers=headers)
        assert removed.status_code == 204
        assert not (data_dir / "voice" / "references" / name).exists()

        rejected = client.post(
            "/api/voice/references",
            headers=headers,
            files={"reference": ("not-audio.txt", b"no", "text/plain")},
        )
        assert rejected.status_code == 400


def test_session_crud_with_header_auth_and_temporary_data_directory(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "private-data"
    workspace = tmp_path / "workspace"
    replacement_workspace = tmp_path / "replacement"
    workspace.mkdir()
    replacement_workspace.mkdir()
    app = create_app(data_dir)

    with TestClient(app) as client:
        headers = {"X-Alice-Token": app.state.session_token}
        created_response = client.post(
            "/api/sessions",
            headers=headers,
            json={
                "title": "API conversation",
                "workspace": str(workspace),
                "provider_id": "ollama",
                "model": "local-model",
            },
        )
        assert created_response.status_code == 200
        created = created_response.json()
        assert created["title"] == "API conversation"
        assert Path(created["workspace"]) == workspace.resolve()
        assert created["provider_id"] == "ollama"
        assert created["model"] == "local-model"

        fetched = client.get(f"/api/sessions/{created['id']}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["messages"] == []

        updated = client.patch(
            f"/api/sessions/{created['id']}",
            headers=headers,
            json={
                "title": "Renamed",
                "workspace": str(replacement_workspace),
                "model": "replacement-model",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["title"] == "Renamed"
        assert Path(updated.json()["workspace"]) == replacement_workspace.resolve()
        assert updated.json()["model"] == "replacement-model"

        missing_workspace = client.patch(
            f"/api/sessions/{created['id']}",
            headers=headers,
            json={"workspace": str(tmp_path / "does-not-exist")},
        )
        assert missing_workspace.status_code == 400

        deleted = client.delete(f"/api/sessions/{created['id']}", headers=headers)
        assert deleted.status_code == 204
        assert client.get(f"/api/sessions/{created['id']}", headers=headers).status_code == 404

    assert (data_dir / "settings.json").is_file()
    assert (data_dir / "alice.db").is_file()


def test_huggingface_endpoints_use_authenticated_local_api(monkeypatch, tmp_path: Path) -> None:
    async def fake_files(repository: str, revision: str, token: str = "") -> dict[str, object]:
        assert (repository, revision) == ("org/example", "main")
        assert token in {"", "token-from-form"}
        return {
            "repository": repository,
            "revision": revision,
            "gguf_files": [{"filename": "model.gguf", "size": 123}],
            "file_count": 1,
            "total_size": 123,
            "format": "gguf",
        }

    async def fake_import(**kwargs: object) -> dict[str, object]:
        assert kwargs["repository"] == "org/example"
        assert kwargs["filename"] == "model.gguf"
        return {"model": "alice", "runtime": "ollama"}

    async def fake_download(**kwargs: object) -> dict[str, object]:
        assert kwargs["repository"] == "https://huggingface.co/Qwen/Qwen2.5-Omni-3B"
        return {"runtime": "downloaded", "download_dir": "C:/models/qwen"}

    monkeypatch.setattr("alice_os.api.inspect_huggingface_repository", fake_files)
    monkeypatch.setattr("alice_os.api.import_huggingface_gguf", fake_import)
    monkeypatch.setattr("alice_os.api.download_huggingface_repository", fake_download)
    app = create_app(tmp_path / "data")

    with TestClient(app) as client:
        headers = {"X-Alice-Token": app.state.session_token}
        files = client.get("/api/huggingface/files?repository=org/example", headers=headers)
        assert files.status_code == 200
        assert files.json()["files"] == [{"filename": "model.gguf", "size": 123}]

        inspected = client.post(
            "/api/huggingface/inspect",
            headers=headers,
            json={"repository": "org/example", "token": "token-from-form"},
        )
        assert inspected.status_code == 200

        imported = client.post(
            "/api/huggingface/import",
            headers=headers,
            json={"repository": "org/example", "filename": "model.gguf"},
        )
        assert imported.status_code == 200
        assert imported.json() == {"model": "alice", "runtime": "ollama"}

        downloaded = client.post(
            "/api/huggingface/download",
            headers=headers,
            json={"repository": "https://huggingface.co/Qwen/Qwen2.5-Omni-3B"},
        )
        assert downloaded.status_code == 200
        job = downloaded.json()
        assert job["status"] in {"queued", "downloading"}
        status_response = client.get(f"/api/huggingface/downloads/{job['id']}", headers=headers)
        assert status_response.status_code == 200
        assert status_response.json()["status"] in {"downloading", "complete"}


def test_workspace_browser_endpoints_stay_inside_selected_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    nested = workspace / "src"
    nested.mkdir(parents=True)
    (nested / "example.py").write_text("print('Alice')\n", encoding="utf-8")
    app = create_app(tmp_path / "data")

    with TestClient(app) as client:
        headers = {"X-Alice-Token": app.state.session_token}
        listed = client.get(
            "/api/workspace/files",
            headers=headers,
            params={"workspace": str(workspace), "path": "."},
        )
        assert listed.status_code == 200
        assert listed.json()["entries"] == [{"path": "src", "type": "directory"}]

        previewed = client.get(
            "/api/workspace/read",
            headers=headers,
            params={"workspace": str(workspace), "path": "src/example.py"},
        )
        assert previewed.status_code == 200
        assert "print('Alice')" in previewed.json()["content"]

        escaped = client.get(
            "/api/workspace/read",
            headers=headers,
            params={"workspace": str(workspace), "path": "../outside.py"},
        )
        assert escaped.status_code == 400

        git = client.get(
            "/api/workspace/git", headers=headers, params={"workspace": str(workspace)}
        )
        assert git.status_code == 200
        assert git.json()["available"] is False


def test_model_library_endpoint_is_authenticated(monkeypatch, tmp_path: Path) -> None:
    async def fake_library(_: Path) -> dict[str, object]:
        return {"ollama": [{"name": "qwen3:4b"}], "huggingface": [], "total_bytes": 12}

    monkeypatch.setattr("alice_os.api.local_model_library", fake_library)
    app = create_app(tmp_path / "data")
    with TestClient(app) as client:
        assert client.get("/api/models/library").status_code == 401
        response = client.get(
            "/api/models/library", headers={"X-Alice-Token": app.state.session_token}
        )
        assert response.status_code == 200
        assert response.json()["ollama"][0]["name"] == "qwen3:4b"
