"""Explicitly paired LAN inference workers. No remote filesystem/process access."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import ssl
import time
from dataclasses import asdict
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx
import psutil
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .config import ConfigStore
from .gpu_bridge import GPUBridges, GPUWorker
from .models import AssistantTurn, ProviderProfile, ToolCall
from .providers import ProviderError, ToolsUnsupportedError, chat, list_models
from .secure_store import SecretStore


class WorkerSettings(BaseModel):
    enabled: bool = False
    provider_id: str = "ollama"
    max_parallel: int = Field(default=1, ge=1, le=8)


class GPUStart(BaseModel):
    device: str = Field(min_length=1, max_length=80)


class PairRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=80)


class JoinRequest(PairRequest):
    url: str = Field(max_length=500)
    ca_pem: str = Field(default="", max_length=20000)


class InferenceRequest(BaseModel):
    model: str = Field(min_length=1, max_length=1000)
    messages: list[dict[str, Any]] = Field(max_length=200)
    tools: list[dict[str, Any]] | None = Field(default=None, max_length=100)


class WorkerStatus(BaseModel):
    node_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    name: str = Field(min_length=1, max_length=255)
    models: list[str] = Field(max_length=10000)
    cpu_count: int | None = Field(default=None, ge=1)
    available_ram: int = Field(ge=0)
    active_jobs: int = Field(ge=0)
    max_parallel: int = Field(ge=1, le=8)
    protocol: Literal[1]
    gpu: dict = Field(default_factory=dict)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def validate_worker_url(value: str) -> str:
    url = urlsplit(value)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.path not in {"", "/"}):
        raise ValueError("Worker address must be an HTTPS origin, such as https://alice-worker.local:7788")
    return value.rstrip("/")


class Cluster:
    def __init__(self, config: ConfigStore):
        self.config = config
        self.path = config.data_dir / "cluster.json"
        self.data = json.loads(self.path.read_text("utf-8")) if self.path.exists() else {
            "node_id": secrets.token_hex(16), "worker": WorkerSettings().model_dump(),
            "controllers": {}, "nodes": {},
        }
        self.pair_hash = ""
        self.pair_expires = 0.0
        self.tasks: dict[asyncio.Task, str] = {}
        self.gpu = GPUWorker(config.data_dir)
        self.bridges = GPUBridges(self)
        self.save()

    def save(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def secret(self, node_id: str) -> SecretStore:
        # IDs used here are generated locally, never supplied by a remote worker.
        return SecretStore(self.config.data_dir / "secrets" / f"cluster-{node_id}")

    def local_profile(self) -> ProviderProfile:
        try:
            profile = self.config.get_provider(self.data["worker"]["provider_id"])
        except KeyError as error:
            raise ProviderError("The shared local provider no longer exists") from error
        host = urlsplit(profile.base_url).hostname or ""
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host == "localhost"
        if profile.kind == "cluster" or not loopback:
            raise ProviderError("Workers may share only a loopback model provider")
        return profile

    async def capabilities(self) -> dict:
        try:
            models = []
            if self.data["worker"]["enabled"]:
                profile = self.local_profile()
                models = await list_models(profile)
        except ProviderError:
            if not self.gpu.status()["running"]:
                raise
            models = []
        return {
            "node_id": self.data["node_id"], "name": socket.gethostname(),
            "models": models, "cpu_count": psutil.cpu_count(),
            "available_ram": psutil.virtual_memory().available,
            "active_jobs": len(self.tasks), "max_parallel": self.data["worker"]["max_parallel"],
            "protocol": 1,
            "gpu": self.gpu.status(),
        }

    def client(self, node: dict) -> httpx.AsyncClient:
        context = ssl.create_default_context()
        if node.get("ca_pem"):
            context.load_verify_locations(cadata=node["ca_pem"])
        return httpx.AsyncClient(
            base_url=node["url"], verify=context, trust_env=False,
            follow_redirects=False, timeout=httpx.Timeout(300, connect=10),
        )

    def node(self, profile: ProviderProfile) -> tuple[dict, dict]:
        node = self.data["nodes"].get(profile.id)
        if not node:
            raise ProviderError("Worker is no longer paired. Open Cluster to pair it again.")
        token = self.secret(profile.id).get()
        if not token:
            raise ProviderError("Worker credential is missing. Pair the worker again.")
        return node, {"Authorization": f"Bearer {token}"}

    async def status(self, profile: ProviderProfile) -> dict:
        node, headers = self.node(profile)
        try:
            async with self.client(node) as client:
                response = await client.get("/api/cluster/worker/status", headers=headers, timeout=10)
                response.raise_for_status()
                return WorkerStatus.model_validate(response.json()).model_dump()
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderError("Worker unavailable; check its address, certificate and pairing") from error

    async def list_models(self, profile: ProviderProfile) -> list[str]:
        return (await self.status(profile))["models"]

    async def chat(self, profile: ProviderProfile, *, model, messages, tools=None, on_token=None):
        node, headers = self.node(profile)
        try:
            async with self.client(node) as client:
                async with client.stream("POST", "/api/cluster/worker/chat", headers=headers,
                                         json={"model": model, "messages": messages, "tools": tools}) as response:
                    if response.status_code == 429:
                        raise ProviderError("Worker is busy; wait for its current job or select another worker")
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        event = json.loads(line)
                        if event["type"] == "token" and on_token:
                            await on_token(event["text"])
                        elif event["type"] == "tools_unsupported":
                            raise ToolsUnsupportedError("Worker model does not support native tools")
                        elif event["type"] == "error":
                            raise ProviderError("Worker inference failed; check the worker's local model service")
                        elif event["type"] == "result":
                            return AssistantTurn(content=event["content"], tool_calls=[
                                ToolCall(**call) for call in event["tool_calls"]])
            raise ProviderError("Worker disconnected before returning a result; request was not retried")
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise ProviderError("Remote inference connection failed; request was not retried") from error

    async def shutdown(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def mount_cluster(app: FastAPI, cluster: Cluster, require_session):
    admin = [Depends(require_session)]

    def require_tls(request: Request):
        if request.url.scheme not in {"https", "wss"}:
            raise HTTPException(400, "Cluster connections require HTTPS; restart Alice with --https")

    async def require_worker(request: Request):
        require_tls(request)
        if not cluster.data["worker"]["enabled"] and not cluster.gpu.status()["running"]:
            raise HTTPException(403, "Worker sharing is disabled")
        supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
        for identity, controller in cluster.data["controllers"].items():
            if hmac.compare_digest(digest(supplied), controller["hash"]):
                return identity
        raise HTTPException(401, "Worker credential is invalid or revoked")

    @app.get("/api/cluster", dependencies=admin)
    async def overview():
        async def inspect(identity, node):
            try:
                state = await cluster.status(cluster.config.get_provider(identity))
                return {"id": identity, "url": node["url"], "online": True, **state,
                        "hostname": state["name"], "name": node["name"]}
            except (ProviderError, KeyError):
                return {"id": identity, "url": node["url"], "name": node["name"], "online": False}
        nodes = await asyncio.gather(*(inspect(key, value)
                                      for key, value in cluster.data["nodes"].items()))
        ca = cluster.config.data_dir / "tls" / "alice-local-ca.crt"
        return {"worker": cluster.data["worker"], "nodes": nodes, "gpu": cluster.gpu.status(),
                "controllers": [{"id": key, "name": value["name"]}
                                for key, value in cluster.data["controllers"].items()],
                "ca_pem": ca.read_text("utf-8") if ca.exists() else ""}

    @app.put("/api/cluster/worker", dependencies=admin)
    async def configure(body: WorkerSettings):
        old = cluster.data["worker"]
        cluster.data["worker"] = body.model_dump()
        try:
            if body.enabled:
                cluster.local_profile()
        except ProviderError as error:
            cluster.data["worker"] = old
            raise HTTPException(400, str(error)) from error
        cluster.pair_hash = ""
        # Changing sharing configuration terminates previous inference requests.
        await cluster.shutdown()
        cluster.save()
        return cluster.data["worker"]

    @app.post("/api/cluster/pairing", dependencies=admin)
    async def pairing(request: Request):
        require_tls(request)
        if not cluster.data["worker"]["enabled"] and not cluster.gpu.status()["running"]:
            raise HTTPException(400, "Enable worker sharing first")
        code = secrets.token_urlsafe(24)
        cluster.pair_hash = digest(code)
        cluster.pair_expires = time.monotonic() + 300
        return {"code": code, "expires_in": 300}

    @app.post("/api/cluster/worker/pair")
    async def accept_pair(body: PairRequest, request: Request):
        require_tls(request)
        if ((not cluster.data["worker"]["enabled"] and not cluster.gpu.status()["running"]) or not cluster.pair_hash
                or time.monotonic() >= cluster.pair_expires
                or not hmac.compare_digest(digest(body.code), cluster.pair_hash)):
            raise HTTPException(401, "Pairing code is invalid or expired")
        cluster.pair_hash = ""
        identity, token = secrets.token_hex(16), secrets.token_urlsafe(32)
        cluster.data["controllers"][identity] = {"name": body.name, "hash": digest(token)}
        cluster.save()
        return {"token": token, "controller_id": identity, "protocol": 1}

    @app.post("/api/cluster/nodes", dependencies=admin)
    async def join(body: JoinRequest):
        try:
            url = validate_worker_url(body.url)
            if any(node["url"] == url for node in cluster.data["nodes"].values()):
                raise HTTPException(409, "This worker address is already paired")
            node = {"url": url, "ca_pem": body.ca_pem, "name": body.name}
            async with cluster.client(node) as client:
                response = await client.post("/api/cluster/worker/pair",
                                             json={"code": body.code, "name": socket.gethostname()[:80]}, timeout=15)
                response.raise_for_status()
                result = response.json()
                if result.get("protocol") != 1:
                    raise ValueError("Worker protocol is incompatible")
            identity = "cluster_" + secrets.token_hex(16)
            cluster.secret(identity).set(result["token"])
            cluster.data["nodes"][identity] = node
            cluster.save()
            cluster.config.upsert_provider(ProviderProfile(
                id=identity, name=f"Worker: {body.name}", kind="cluster", base_url=url))
            return {"id": identity}
        except (httpx.HTTPError, ValueError, KeyError, ssl.SSLError) as error:
            raise HTTPException(400, "Pairing failed. Check HTTPS address, trusted CA and fresh pairing code.") from error

    @app.delete("/api/cluster/nodes/{identity}", dependencies=admin)
    async def forget(identity: str):
        if identity not in cluster.data["nodes"]:
            raise HTTPException(404, "Unknown worker")
        del cluster.data["nodes"][identity]
        await cluster.bridges.close(identity)
        cluster.save()
        cluster.secret(identity).path.unlink(missing_ok=True)
        cluster.config.delete_provider(identity)
        return {"removed": True}

    @app.delete("/api/cluster/controllers/{identity}", dependencies=admin)
    async def revoke(identity: str):
        if identity not in cluster.data["controllers"]:
            raise HTTPException(404, "Unknown controller")
        del cluster.data["controllers"][identity]
        await cluster.gpu.revoke(identity)
        cluster.save()
        for task, owner in list(cluster.tasks.items()):
            if owner == identity:
                task.cancel()
        return {"revoked": True}

    @app.get("/api/cluster/worker/status")
    async def worker_status(identity: str = Depends(require_worker)):
        try:
            return await cluster.capabilities()
        except ProviderError as error:
            raise HTTPException(503, str(error)) from error

    @app.post("/api/cluster/worker/chat")
    async def inference(body: InferenceRequest, identity: str = Depends(require_worker)):
        if not cluster.data["worker"]["enabled"]:
            raise HTTPException(403, "Inference sharing is disabled")
        if len(cluster.tasks) >= cluster.data["worker"]["max_parallel"]:
            raise HTTPException(429, "Worker is at capacity")
        try:
            profile = cluster.local_profile()
        except ProviderError as error:
            raise HTTPException(503, str(error)) from error
        queue: asyncio.Queue = asyncio.Queue(maxsize=64)

        async def token(text):
            await queue.put({"type": "token", "text": text})

        async def execute():
            try:
                result = await chat(profile, model=body.model, messages=body.messages,
                                    tools=body.tools, on_token=token)
                await queue.put({"type": "result", **asdict(result)})
            except ToolsUnsupportedError:
                await queue.put({"type": "tools_unsupported"})
            except Exception:
                await queue.put({"type": "error"})

        task = asyncio.create_task(execute())
        cluster.tasks[task] = identity

        async def events():
            try:
                while True:
                    get = asyncio.create_task(queue.get())
                    try:
                        await asyncio.wait({get, task}, return_when=asyncio.FIRST_COMPLETED)
                        if not get.done() and queue.empty():
                            yield json.dumps({"type": "error"}) + "\n"
                            break
                        event = await get
                    finally:
                        if not get.done():
                            get.cancel()
                        await asyncio.gather(get, return_exceptions=True)
                    yield json.dumps(event) + "\n"
                    if event["type"] != "token":
                        break
            finally:
                task.cancel()
                cluster.tasks.pop(task, None)
                await asyncio.gather(task, return_exceptions=True)

        return StreamingResponse(events(), media_type="application/x-ndjson")

    @app.get("/api/gpu", dependencies=admin)
    async def local_gpu():
        try:
            return {**cluster.gpu.status(), "devices": await cluster.gpu.devices()}
        except (OSError, RuntimeError, TimeoutError) as error:
            raise HTTPException(400, str(error) or "GPU discovery timed out") from error

    @app.post("/api/gpu/start", dependencies=admin)
    async def start_gpu(body: GPUStart):
        try:
            return await cluster.gpu.start(body.device)
        except (OSError, RuntimeError, TimeoutError) as error:
            raise HTTPException(400, str(error) or "GPU sharing timed out") from error

    @app.post("/api/gpu/stop", dependencies=admin)
    async def stop_gpu():
        await cluster.gpu.stop()
        cluster.pair_hash = ""
        return cluster.gpu.status()

    @app.websocket("/api/cluster/worker/gpu/tunnel")
    async def gpu_tunnel(websocket: WebSocket):
        # Only paired machine credentials; browser origins are never accepted.
        if websocket.headers.get("origin"):
            await websocket.close(code=1008)
            return
        try:
            identity = await require_worker(websocket)
        except HTTPException:
            await websocket.close(code=1008)
            return
        await cluster.gpu.tunnel(websocket, identity)
