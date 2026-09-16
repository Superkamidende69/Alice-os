import asyncio
import json
import socket
import ssl
import threading
import time

import httpx
import pytest
import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from fastapi import FastAPI, HTTPException, Request

from alice_os import cluster as module
from alice_os.api import create_app
from alice_os.auth import create_auth_file
from alice_os.cluster import Cluster, mount_cluster, validate_worker_url
from alice_os.config import ConfigStore
from alice_os.models import AssistantTurn, ProviderProfile, ToolCall
from alice_os.providers import ProviderError, ToolsUnsupportedError
from alice_os.tls import ensure_tls_certificate


def make_worker(tmp_path):
    cluster = Cluster(ConfigStore(tmp_path))
    app = FastAPI()

    def admin(request: Request):
        if request.headers.get("X-Admin") != "test-admin":
            raise HTTPException(401)

    mount_cluster(app, cluster, admin)
    return app, cluster


async def pair(client):
    admin = {"X-Admin": "test-admin"}
    response = await client.put("/api/cluster/worker", headers=admin,
                                json={"enabled": True, "provider_id": "ollama"})
    assert response.status_code == 200
    code = (await client.post("/api/cluster/pairing", headers=admin)).json()["code"]
    response = await client.post("/api/cluster/worker/pair", json={"code": code, "name": "Controller"})
    assert response.status_code == 200
    return code, response.json()


@pytest.mark.parametrize("url", ["http://192.168.1.2:7788", "https://user:pass@worker",
                                  "https://worker/path", "https://worker?x=1", "https://worker#x"])
def test_worker_requires_https_origin(url):
    with pytest.raises(ValueError):
        validate_worker_url(url)


def test_legacy_ca_upgrade_preserves_its_key_and_caches_new_certificate(tmp_path):
    ca, cert, _ = ensure_tls_certificate(tmp_path, "localhost")
    key_path = tmp_path / "tls" / "alice-local-ca.key"
    original_key = key_path.read_bytes()
    key = serialization.load_pem_private_key(original_key, password=None)
    current = x509.load_pem_x509_certificate(ca.read_bytes())
    legacy = (x509.CertificateBuilder().subject_name(current.subject)
              .issuer_name(current.issuer).public_key(key.public_key())
              .serial_number(current.serial_number)
              .not_valid_before(current.not_valid_before_utc)
              .not_valid_after(current.not_valid_after_utc)
              .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
              .sign(key, hashes.SHA256()))
    ca.write_bytes(legacy.public_bytes(serialization.Encoding.PEM))
    metadata_path = tmp_path / "tls" / "alice-server.json"
    metadata = json.loads(metadata_path.read_text())
    metadata.pop("certificate_version")
    metadata_path.write_text(json.dumps(metadata))
    ensure_tls_certificate(tmp_path, "localhost")
    assert key_path.read_bytes() == original_key
    upgraded = x509.load_pem_x509_certificate(ca.read_bytes())
    assert upgraded.extensions.get_extension_for_class(x509.KeyUsage).value.key_cert_sign
    assert upgraded.public_key().public_numbers() == current.public_key().public_numbers()
    server_bytes = cert.read_bytes()
    ensure_tls_certificate(tmp_path, "localhost")
    assert cert.read_bytes() == server_bytes


async def test_pairing_expiry_replay_revocation_and_persistence(tmp_path, monkeypatch):
    app, cluster = make_worker(tmp_path)

    async def models(profile):
        return ["test-model"]

    monkeypatch.setattr(module, "list_models", models)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://worker") as client:
        assert (await client.get("/api/cluster")).status_code == 401
        assert (await client.get("/api/cluster/worker/status")).status_code == 403
        code, result = await pair(client)
        headers = {"Authorization": f"Bearer {result['token']}"}
        assert (await client.post("/api/cluster/worker/pair", json={"code": code, "name": "Replay"})).status_code == 401
        assert (await client.get("/api/cluster/worker/status")).status_code == 401
        assert (await client.get("/api/cluster/worker/status", headers=headers)).json()["models"] == ["test-model"]
        saved = cluster.path.read_text()
        assert result["token"] not in saved and code not in saved
        assert Cluster(cluster.config).data["controllers"] == cluster.data["controllers"]
        admin = {"X-Admin": "test-admin"}
        code = (await client.post("/api/cluster/pairing", headers=admin)).json()["code"]
        cluster.pair_expires = time.monotonic() - 1
        assert (await client.post("/api/cluster/worker/pair", json={"code": code, "name": "Expired"})).status_code == 401
        assert (await client.delete(f"/api/cluster/controllers/{result['controller_id']}", headers=admin)).status_code == 200
        assert (await client.get("/api/cluster/worker/status", headers=headers)).status_code == 401
        assert (await client.get("/api/cluster/worker/status", headers={**headers, "Authorization": "bad"})).status_code == 401


async def test_http_pairing_is_rejected_and_remote_provider_cannot_be_shared(tmp_path):
    app, cluster = make_worker(tmp_path)
    cluster.config.upsert_provider(ProviderProfile(id="remote", name="Remote", kind="openai", base_url="https://other"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://worker") as client:
        response = await client.put("/api/cluster/worker", headers={"X-Admin": "test-admin"},
                                    json={"enabled": True, "provider_id": "remote"})
        assert response.status_code == 400
        assert not cluster.data["worker"]["enabled"]
        assert (await client.post("/api/cluster/pairing", headers={"X-Admin": "test-admin"})).status_code == 400


async def test_controller_worker_integration_and_agent_run(tmp_path, monkeypatch):
    worker_app, worker = make_worker(tmp_path / "worker")
    controller_app = create_app(tmp_path / "controller")
    controller = controller_app.state.cluster

    async def models(profile):
        return ["tiny-model"]

    requests = []

    async def infer(profile, **kwargs):
        requests.append(kwargs)
        assert profile.id == "ollama"
        await kwargs["on_token"]("Hello")
        return AssistantTurn(content="Hello")

    monkeypatch.setattr(module, "list_models", models)
    monkeypatch.setattr(module, "chat", infer)
    monkeypatch.setattr("alice_os.api.list_models", models)
    monkeypatch.setattr(Cluster, "client", lambda self, node: httpx.AsyncClient(
        transport=httpx.ASGITransport(app=worker_app), base_url=node["url"]))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=worker_app), base_url="https://worker") as remote:
        admin = {"X-Admin": "test-admin"}
        await remote.put("/api/cluster/worker", headers=admin, json={"enabled": True, "provider_id": "ollama"})
        code = (await remote.post("/api/cluster/pairing", headers=admin)).json()["code"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=controller_app), base_url="https://testserver") as client:
        page = await client.get("/cluster")
        assert page.status_code == 200 and "More machines" in page.text
        response = await client.post("/api/cluster/nodes", json={"url": "https://worker", "name": "GPU PC", "code": code})
        assert response.status_code == 200, response.text
        identity = response.json()["id"]
        profile = controller.config.get_provider(identity)
        assert profile.kind == "cluster"
        assert await controller.list_models(profile) == ["tiny-model"]
        overview = (await client.get("/api/cluster")).json()
        assert overview["nodes"][0]["online"]
        assert "token" not in json.dumps(overview)
        catalog = (await client.get("/api/models/catalog")).json()
        assert any(model["provider_id"] == identity for model in catalog["models"])
        assert (await client.post("/api/providers", json=profile.model_dump())).status_code == 400
        assert (await client.delete(f"/api/providers/{identity}")).status_code == 400
        session = controller_app.state.storage.create_session(workspace=str(tmp_path))
        run = controller_app.state.runs.start(session_id=session["id"], user_message="Hi",
                                               provider_id=identity, model="tiny-model", agent_mode=False)
        await run.task
        assert run.events[-1].name == "done"
        assert any(event.name == "token" and event.data["text"] == "Hello" for event in run.events)
        assert requests[0]["messages"][-1]["content"] == "Hi"
        saved_token = controller.secret(identity).get()
        assert saved_token not in controller.path.read_text()
        assert Cluster(controller.config).secret(identity).get() == saved_token
        assert (await client.delete(f"/api/cluster/nodes/{identity}")).status_code == 200
        assert not controller.secret(identity).path.exists()
        with pytest.raises(ProviderError):
            await controller.list_models(profile)
    await controller_app.state.runs.shutdown()
    controller_app.state.storage.close()


async def test_worker_can_join_existing_network_with_controller_account(tmp_path, monkeypatch):
    """The worker password is only forwarded to the controller for this join."""
    worker_app = create_app(tmp_path / "worker")
    create_auth_file(tmp_path / "controller" / "network-auth.json", "main", "a long test password")
    controller_app = create_app(tmp_path / "controller")

    async def models(profile):
        return ["tiny-model"]

    monkeypatch.setattr(module, "list_models", models)

    def in_memory_client(self, node):
        target = controller_app if node["url"] == "https://controller" else worker_app
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=target), base_url=node["url"])

    monkeypatch.setattr(Cluster, "client", in_memory_client)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=worker_app), base_url="https://testserver") as client:
        await client.get("/cluster")
        configured = await client.put("/api/cluster/worker", json={"enabled": True, "provider_id": "localai"})
        assert configured.status_code == 200, configured.text
        joined = await client.post("/api/cluster/join-network", json={
            "controller_url": "https://controller", "username": "main", "password": "a long test password",
            "name": "New GPU", "url": "https://testserver", "ca_pem": "",
        })
        assert joined.status_code == 200, joined.text
        assert joined.json()["connected"] is True

    controller = controller_app.state.cluster
    worker = worker_app.state.cluster
    assert len(controller.data["nodes"]) == 1
    assert len(worker.data["controllers"]) == 1
    assert "a long test password" not in worker.path.read_text()
    assert "a long test password" not in controller.path.read_text()
    await worker_app.state.runs.shutdown()
    await controller_app.state.runs.shutdown()
    worker_app.state.storage.close()
    controller_app.state.storage.close()


@pytest.mark.parametrize("mode", ["tools", "unsupported", "error"])
async def test_inference_tool_roundtrip_and_failure(tmp_path, monkeypatch, mode):
    app, worker = make_worker(tmp_path / "worker")
    controller = Cluster(ConfigStore(tmp_path / "controller"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://worker") as client:
        _, paired = await pair(client)
    profile = ProviderProfile(id="cluster_test", name="Worker", kind="cluster", base_url="https://worker")
    controller.data["nodes"][profile.id] = {"url": profile.base_url}
    controller.secret(profile.id).set(paired["token"])

    async def infer(profile, **kwargs):
        if mode == "unsupported":
            raise ToolsUnsupportedError("Unsupported")
        if mode == "error":
            raise RuntimeError("private service detail")
        assert kwargs["tools"] == [{"type": "function"}]
        return AssistantTurn(content="", tool_calls=[ToolCall("call1", "workspace_read", {"path": "test.py"})])

    monkeypatch.setattr(module, "chat", infer)
    monkeypatch.setattr(Cluster, "client", lambda self, node: httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=node["url"]))
    if mode == "tools":
        result = await controller.chat(profile, model="test", messages=[], tools=[{"type": "function"}])
        assert result.tool_calls[0].arguments == {"path": "test.py"}
    else:
        with pytest.raises(ToolsUnsupportedError if mode == "unsupported" else ProviderError):
            await controller.chat(profile, model="test", messages=[])
    assert not worker.tasks


async def test_capacity_disconnect_and_revocation_cancel_inference(tmp_path, monkeypatch):
    app, worker = make_worker(tmp_path)
    started, cancelled = asyncio.Event(), asyncio.Event()

    async def infer(*args, **kwargs):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(module, "chat", infer)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://worker") as client:
        _, paired = await pair(client)
        headers = {"Authorization": f"Bearer {paired['token']}"}
        request = asyncio.create_task(client.post("/api/cluster/worker/chat", headers=headers,
                                                 json={"model": "test", "messages": []}))
        await asyncio.wait_for(started.wait(), 2)
        response = await client.post("/api/cluster/worker/chat", headers=headers, json={"model": "test", "messages": []})
        assert response.status_code == 429
        request.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request
        await asyncio.wait_for(cancelled.wait(), 2)
        assert not worker.tasks
        started.clear()
        cancelled.clear()
        request = asyncio.create_task(client.post("/api/cluster/worker/chat", headers=headers,
                                                 json={"model": "test", "messages": []}))
        await asyncio.wait_for(started.wait(), 2)
        await client.delete(f"/api/cluster/controllers/{paired['controller_id']}", headers={"X-Admin": "test-admin"})
        await asyncio.wait_for(cancelled.wait(), 2)
        response = await asyncio.wait_for(request, 2)
        assert '"error"' in response.text
        assert not worker.tasks


async def test_real_https_certificate_validation_and_streaming(tmp_path, monkeypatch):
    app, worker = make_worker(tmp_path / "worker")
    worker.data["worker"] = {"enabled": True, "provider_id": "ollama", "max_parallel": 1}

    async def infer(profile, **kwargs):
        await kwargs["on_token"]("Secure ")
        await kwargs["on_token"]("reply")
        return AssistantTurn(content="Secure reply")

    monkeypatch.setattr(module, "chat", infer)
    ca, cert, key = ensure_tls_certificate(tmp_path / "worker", "localhost")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", ssl_certfile=str(cert), ssl_keyfile=str(key)))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        for _ in range(200):
            if server.started:
                break
            await asyncio.sleep(.025)
        assert server.started
        url = f"https://localhost:{port}"
        async with httpx.AsyncClient(verify=True, trust_env=False) as untrusted:
            with pytest.raises(httpx.ConnectError):
                await untrusted.get(url + "/api/cluster/worker/status")
        context = ssl.create_default_context(cafile=str(ca))
        async with httpx.AsyncClient(base_url=url, verify=context, trust_env=False) as trusted:
            _, paired = await pair(trusted)
        controller = Cluster(ConfigStore(tmp_path / "controller"))
        profile = ProviderProfile(id="cluster_tls", name="TLS worker", kind="cluster", base_url=url)
        controller.data["nodes"][profile.id] = {"url": url, "ca_pem": ca.read_text()}
        controller.secret(profile.id).set(paired["token"])
        tokens = []

        async def collect(text):
            tokens.append(text)

        result = await controller.chat(profile, model="test", messages=[], on_token=collect)
        assert tokens == ["Secure ", "reply"]
        assert result.content == "Secure reply"
    finally:
        server.should_exit = True
        await asyncio.to_thread(thread.join, 5)
        listener.close()
