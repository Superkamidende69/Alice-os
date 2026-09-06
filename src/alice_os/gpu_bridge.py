"""GPU RPC transported over paired Alice HTTPS connections, never exposed on the LAN."""
from __future__ import annotations

import asyncio
import re
import socket
import ssl
import subprocess
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect
from websockets.asyncio.client import connect

from .distributed import DistributedSettings, probe_devices
from .providers import ProviderError
from .runtimes import RuntimeOperationError, llama_cpp_executable

CHUNK = 256 * 1024


async def relay(left, right):
    tasks = [asyncio.create_task(left()), asyncio.create_task(right())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


class GPUWorker:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.process = None
        self.port = None
        self.device = ""
        self.lock = asyncio.Lock()
        self.connections: dict[asyncio.Task, str] = {}

    def status(self):
        return {"running": self.process is not None and self.process.poll() is None,
                "device": self.device, "connections": len(self.connections)}

    async def devices(self):
        output = await probe_devices(llama_cpp_executable(), DistributedSettings())
        return [{"id": match[1], "name": match[2]} for match in
                re.finditer(r"^\s*([\w.-]+):\s*(.+)$", output, re.MULTILINE)
                if not match[1].startswith("RPC") and match[1] != "CPU"]

    async def start(self, device: str):
        async with self.lock:
            if self.status()["running"]:
                if self.device != device:
                    raise RuntimeOperationError("Stop GPU sharing before choosing another GPU")
                return self.status()
            available = await self.devices()
            if device not in {item["id"] for item in available}:
                raise RuntimeOperationError("Select a GPU detected on this machine")
            executable = llama_cpp_executable().with_name(
                "ggml-rpc-server.exe" if llama_cpp_executable().suffix == ".exe" else "ggml-rpc-server")
            if not executable.is_file():
                raise RuntimeOperationError("The GPU worker executable is missing")
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                self.port = reservation.getsockname()[1]
            logs = self.data_dir / "logs"
            logs.mkdir(exist_ok=True)
            with (logs / "gpu-worker.log").open("ab") as output:
                self.process = subprocess.Popen(
                    [str(executable), "--host", "127.0.0.1", "--port", str(self.port), "--device", device],
                    stdout=output, stderr=output, stdin=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            self.device = device
            try:
                for _ in range(50):
                    if self.process.poll() is not None:
                        raise RuntimeOperationError("GPU sharing failed to start; see logs/gpu-worker.log")
                    try:
                        _, writer = await asyncio.open_connection("127.0.0.1", self.port)
                        writer.close()
                        await writer.wait_closed()
                        return self.status()
                    except OSError:
                        await asyncio.sleep(.1)
                raise RuntimeOperationError("GPU sharing startup timed out")
            except BaseException:
                await self._stop()
                raise

    async def _stop(self):
        await self.revoke(None)
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                await asyncio.to_thread(self.process.wait, timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                await asyncio.to_thread(self.process.wait)
        self.process = None
        self.port = None

    async def stop(self):
        async with self.lock:
            await self._stop()

    async def revoke(self, identity):
        tasks = [task for task, owner in self.connections.items() if identity is None or owner == identity]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def tunnel(self, websocket: WebSocket, identity: str):
        if not self.status()["running"] or len(self.connections) >= 16:
            await websocket.close(code=1013)
            return
        task = asyncio.current_task()
        self.connections[task] = identity
        writer = None
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
            await websocket.accept()

            async def incoming():
                while True:
                    data = await websocket.receive_bytes()
                    if len(data) > CHUNK:
                        raise RuntimeOperationError("GPU frame too large")
                    writer.write(data)
                    await writer.drain()

            async def outgoing():
                while data := await reader.read(CHUNK):
                    await websocket.send_bytes(data)

            await relay(incoming, outgoing)
        except (OSError, WebSocketDisconnect, RuntimeError):
            pass
        finally:
            self.connections.pop(task, None)
            if writer is not None:
                writer.close()
            try:
                await websocket.close()
            except RuntimeError:
                pass


class GPUBridges:
    def __init__(self, cluster):
        self.cluster = cluster
        self.servers = {}
        self.tasks: dict[asyncio.Task, str] = {}
        self.lock = asyncio.Lock()

    async def resolve(self, settings: DistributedSettings) -> DistributedSettings:
        if not settings.enabled or not settings.worker_ids:
            return settings
        async with self.lock:
            endpoints = list(settings.endpoints)
            for identity in settings.worker_ids:
                if identity not in self.cluster.data["nodes"]:
                    raise RuntimeOperationError("A selected GPU worker is no longer paired")
                profile = self.cluster.config.get_provider(identity)
                node = self.cluster.data["nodes"][identity]
                try:
                    status = await self.cluster.status(profile)
                except ProviderError as error:
                    raise RuntimeOperationError(f"Could not connect to {node['name']}; check its Alice connection") from error
                if status.get("node_id") == self.cluster.data["node_id"]:
                    raise RuntimeOperationError("The controller's local GPU is already included; select another machine")
                if not status.get("gpu", {}).get("running"):
                    raise RuntimeOperationError(f"Start GPU sharing on {node['name']} first")
                if identity not in self.servers:
                    async def accept(reader, writer, worker_id=identity):
                        await self.forward(worker_id, reader, writer)
                    self.servers[identity] = await asyncio.start_server(accept, "127.0.0.1", 0)
                port = self.servers[identity].sockets[0].getsockname()[1]
                endpoints.append(f"127.0.0.1:{port}")
            return DistributedSettings(enabled=True, endpoints=endpoints)

    async def forward(self, identity, reader, writer):
        if len(self.tasks) >= 32:
            writer.close()
            return
        task = asyncio.current_task()
        self.tasks[task] = identity
        try:
            profile = self.cluster.config.get_provider(identity)
            node, headers = self.cluster.node(profile)
            context = ssl.create_default_context()
            if node.get("ca_pem"):
                context.load_verify_locations(cadata=node["ca_pem"])
            url = node["url"].replace("https://", "wss://", 1) + "/api/cluster/worker/gpu/tunnel"
            async with connect(url, ssl=context, additional_headers=headers, proxy=None,
                               compression=None, max_size=CHUNK, max_queue=4,
                               open_timeout=10, close_timeout=2) as websocket:
                async def outgoing():
                    while data := await reader.read(CHUNK):
                        await websocket.send(data)

                async def incoming():
                    async for data in websocket:
                        if not isinstance(data, bytes):
                            raise RuntimeOperationError("GPU worker returned an invalid frame")
                        writer.write(data)
                        await writer.drain()

                await relay(incoming, outgoing)
        except Exception:
            # Native discovery reports the failed endpoint; never log credentials.
            pass
        finally:
            self.tasks.pop(task, None)
            writer.close()

    async def close(self, identity=None):
        async with self.lock:
            for key in list(self.servers):
                if identity is None or identity == key:
                    server = self.servers.pop(key)
                    server.close()
                    await server.wait_closed()
            tasks = [task for task, owner in self.tasks.items() if identity is None or identity == owner]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
