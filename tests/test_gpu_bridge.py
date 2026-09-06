import asyncio
import hashlib
import secrets
import socket
import ssl
import threading
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus

from alice_os.api import create_app
from alice_os.cluster import Cluster
from alice_os.config import ConfigStore
from alice_os.distributed import DistributedSettings
from alice_os.models import ProviderProfile
from alice_os.tls import ensure_tls_certificate


def test_gpu_controls_require_auth_and_detected_device(tmp_path, monkeypatch):
    monkeypatch.delenv("ALICE_NETWORK_MODE", raising=False)
    app = create_app(tmp_path)
    monkeypatch.setattr(app.state.cluster.gpu, "devices", AsyncMock(return_value=[{"id": "CUDA0", "name": "Test GPU"}]))
    with TestClient(app) as client:
        assert client.post("/api/gpu/start", json={"device": "CUDA0"}).status_code == 401
        client.get("/")
        assert client.get("/api/gpu").json()["devices"][0]["id"] == "CUDA0"
        assert client.post("/api/gpu/start", json={"device": "bad-device"}).status_code == 400
        assert not app.state.cluster.gpu.status()["running"]


@pytest.mark.parametrize("disconnect", ["revoke", "stop"])
async def test_paired_https_gpu_bridge_preserves_bytes_and_closes_on_revocation(tmp_path, monkeypatch, disconnect):
    monkeypatch.delenv("ALICE_NETWORK_MODE", raising=False)
    app = create_app(tmp_path / "worker")
    worker = app.state.cluster
    token, controller_id = secrets.token_urlsafe(32), secrets.token_hex(16)
    worker.data["controllers"][controller_id] = {"name": "Controller", "hash": hashlib.sha256(token.encode()).hexdigest()}
    # Echo substitutes for the native RPC binary, testing transport without GPU allocation.
    async def echo(reader, writer):
        try:
            while data := await reader.read(65536):
                writer.write(data)
                await writer.drain()
        finally:
            writer.close()

    echo_server = await asyncio.start_server(echo, "127.0.0.1", 0)
    worker.gpu.port = echo_server.sockets[0].getsockname()[1]
    worker.gpu.process = Mock()
    worker.gpu.process.poll.return_value = None
    worker.gpu.device = "CUDA0"
    ca, cert, key = ensure_tls_certificate(tmp_path / "worker", "localhost")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", ssl_certfile=str(cert), ssl_keyfile=str(key)))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    controller = Cluster(ConfigStore(tmp_path / "controller"))
    identity = "cluster_" + secrets.token_hex(16)
    url = f"https://localhost:{port}"
    controller.data["nodes"][identity] = {"url": url, "ca_pem": ca.read_text(), "name": "Worker"}
    controller.config.upsert_provider(ProviderProfile(id=identity, name="Worker", kind="cluster", base_url=url))
    controller.secret(identity).set(token)
    writer = None
    try:
        for _ in range(200):
            if server.started:
                break
            await asyncio.sleep(.025)
        assert server.started
        context = ssl.create_default_context(cafile=str(ca))
        # Neither browser origins nor unauthenticated clients can reach native RPC.
        for headers in ({}, {"Authorization": f"Bearer {token}", "Origin": url}):
            with pytest.raises(InvalidStatus):
                async with connect(f"wss://localhost:{port}/api/cluster/worker/gpu/tunnel", ssl=context, additional_headers=headers, proxy=None):
                    pytest.fail("GPU connection should not be accepted")
        settings = DistributedSettings(enabled=True, worker_ids=[identity])
        resolved = await controller.bridges.resolve(settings)
        endpoint = resolved.endpoints[0]
        reader, writer = await asyncio.open_connection("127.0.0.1", int(endpoint.split(":")[1]))
        payload = bytes(range(256)) * 4096
        writer.write(payload)
        await writer.drain()
        assert await asyncio.wait_for(reader.readexactly(len(payload)), 10) == payload
        async with httpx.AsyncClient(base_url=url, verify=context, trust_env=False) as client:
            await client.get("/")
            response = (await client.delete(f"/api/cluster/controllers/{controller_id}")
                        if disconnect == "revoke" else await client.post("/api/gpu/stop"))
            assert response.status_code == 200
        assert await asyncio.wait_for(reader.read(), 5) == b""
    finally:
        if writer:
            writer.close()
        await controller.bridges.close()
        server.should_exit = True
        await asyncio.to_thread(thread.join, 5)
        listener.close()
        echo_server.close()
        await echo_server.wait_closed()
