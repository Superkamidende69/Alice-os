import socket
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from alice_os.api import create_app
from alice_os.world_view import WorldView, is_host_client


def test_world_page_and_controls_require_local_authenticated_client(tmp_path, monkeypatch):
    monkeypatch.setattr("alice_os.world_view.psutil.net_if_addrs", lambda: {
        "Ethernet": [SimpleNamespace(family=socket.AF_INET, address="10.0.0.252")],
    })
    monkeypatch.setenv("ALICE_GODS_EYE_HOME", str(tmp_path / "missing"))
    app = create_app(tmp_path / "data")
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/world/status").status_code == 401
        assert client.post("/api/world/start").status_code == 401
        page = client.get("/world")
        assert page.status_code == 200
        assert 'id="world-start"' in page.text
        status = client.get("/api/world/status").json()
        assert status["installed"] is False
        assert status["url"] is None
        assert status["can_control"] is True
        assert client.post("/api/world/start").status_code == 409
        assert client.post("/api/world/stop").json()["running"] is False
        assert client.post("/api/world/start", headers={"Origin": "https://foreign.example"}).status_code == 403
    with TestClient(create_app(tmp_path / "remote"), client=("192.168.1.99", 50000)) as client:
        client.get("/")
        status = client.get("/api/world/status")
        assert status.status_code == 200
        assert status.json()["can_control"] is False
        assert status.json()["url"] is None
        assert client.post("/api/world/start").status_code == 403
        assert client.post("/api/world/stop").status_code == 403
    with TestClient(create_app(tmp_path / "same-host"), client=("10.0.0.252", 50000)) as client:
        client.get("/world")
        assert client.get("/api/world/status").json()["can_control"] is True
        assert client.post("/api/world/stop").status_code == 200
        assert client.post("/api/world/start").status_code == 409  # Missing install, not forbidden.


def test_host_recognition_does_not_trust_arbitrary_lan_peers(monkeypatch):
    monkeypatch.setattr("alice_os.world_view.psutil.net_if_addrs", lambda: {
        "Ethernet": [SimpleNamespace(family=socket.AF_INET, address="10.0.0.252")],
    })
    assert is_host_client("10.0.0.252")
    assert is_host_client("::ffff:10.0.0.252")
    assert is_host_client("::1")
    assert not is_host_client("10.0.0.253")
    assert not is_host_client("0.0.0.0")
    assert not is_host_client("aliceos.local")  # Never authorize by an unverified name.


@pytest.mark.asyncio
async def test_occupied_port_is_not_adopted_or_killed(tmp_path, monkeypatch):
    root = tmp_path / "gev"
    vite = root / "node_modules/vite/bin/vite.js"
    vite.parent.mkdir(parents=True)
    vite.touch()
    service = WorldView(tmp_path, root)
    service.node = sys.executable
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        monkeypatch.setattr("alice_os.world_view.PORT", listener.getsockname()[1])
        popen = MagicMock(side_effect=AssertionError("Must not start on occupied port"))
        monkeypatch.setattr("alice_os.world_view.subprocess.Popen", popen)
        with pytest.raises(RuntimeError, match="occupied"):
            await service.start()
        await service.stop()
        assert listener.fileno() >= 0
        popen.assert_not_called()


@pytest.mark.asyncio
async def test_process_is_owned_idempotent_and_excludes_alice_secrets(tmp_path, monkeypatch):
    vite = tmp_path / "node_modules/vite/bin/vite.js"
    vite.parent.mkdir(parents=True)
    vite.touch()
    service = WorldView(tmp_path, tmp_path)
    service.node = sys.executable
    process = MagicMock(pid=999999999)
    process.poll.return_value = None
    popen = MagicMock(return_value=process)
    monkeypatch.setattr("alice_os.world_view.subprocess.Popen", popen)
    monkeypatch.setenv("OPENAI_API_KEY", "test-do-not-inherit")
    monkeypatch.setenv("ALICE_NETWORK_TOKEN", "test-do-not-inherit")
    # Reserve a free test port only for the conflict check; HTTP is mocked below.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    monkeypatch.setattr("alice_os.world_view.PORT", port)

    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url):
            return MagicMock(status_code=200, text="<html><title>God's Eye View</title></html>")

    monkeypatch.setattr("alice_os.world_view.httpx.AsyncClient", Client)
    assert (await service.start())["ready"]
    assert (await service.start())["ready"]
    popen.assert_called_once()
    env = popen.call_args.kwargs["env"]
    assert "OPENAI_API_KEY" not in env
    assert "ALICE_NETWORK_TOKEN" not in env
    assert env["HOST"] == "127.0.0.1"
    assert "--strictPort" in popen.call_args.args[0]
    await service.stop()
    await service.stop()
    process.terminate.assert_called_once()
    assert service.status()["url"] is None
