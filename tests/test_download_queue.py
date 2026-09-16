from pathlib import Path

from fastapi.testclient import TestClient

from alice_os.api import create_app


def test_repeated_install_reuses_active_transfer(tmp_path: Path) -> None:
    app = create_app(tmp_path / "data")
    with TestClient(app) as client:
        client.get("/")
        for status in ("queued", "downloading"):
            job = {"id": "existing", "model": "test-model", "variant": "q4", "status": status}
            app.state.localai_download_jobs["existing"] = job
            for _ in range(2):
                response = client.post("/api/localai/models/install", json={"name": "test-model", "variant": "q4"})
                assert response.status_code == 200
                assert response.json()["id"] == "existing"
            assert len(app.state.localai_download_jobs) == 1


def test_completed_download_is_not_returned_as_active(tmp_path: Path, monkeypatch) -> None:
    import alice_os.api as api_module
    from alice_os.runtimes import RuntimeOperationError

    async def fake_download(**kwargs):
        raise RuntimeOperationError("Test download failure; no network used")

    monkeypatch.setattr(api_module, "download_alice_model", fake_download)
    app = create_app(tmp_path / "data")
    with TestClient(app) as client:
        client.get("/")
        app.state.localai_download_jobs["old"] = {
            "id": "old", "model": "test-model", "variant": "", "status": "complete"
        }
        response = client.post("/api/localai/models/install", json={"name": "test-model"})
        assert response.status_code == 200
        assert response.json()["id"] != "old"
