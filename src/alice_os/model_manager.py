"""One inventory for local GGUF files and ownership-checked runtime switching."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import httpx
import psutil

from .distributed import DistributedStore, matches_settings, probe_devices
from .models import ProviderProfile
from .runtimes import RuntimeOperationError, llama_cpp_executable


def inventory(data_dir: Path) -> list[dict]:
    root = (data_dir / "models").resolve()
    entries = []
    seen = set()
    for path in sorted(root.rglob("*.gguf")):
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or resolved in seen or ".cache" in path.parts:
            continue
        seen.add(resolved)
        relative = resolved.relative_to(root).as_posix()
        entries.append({
            "id": relative, "name": path.stem, "model_path": relative,
            "location": str(resolved), "size": path.stat().st_size,
            "model_size_bytes": path.stat().st_size, "size_source": "Local file",
            "format": "GGUF", "backend": "llama-cpp", "installed": True,
            "source": "Hugging Face" if relative.startswith("huggingface/") else "Alice",
            "status": "Downloaded", "ready": False,
        })
    return entries


class ModelManager:
    def __init__(self, config):
        self.config = config
        self.lock = asyncio.Lock()
        self.distributed = DistributedStore(config.data_dir)
        self.bridges = None

    def owned_listener(self):
        executable = llama_cpp_executable().resolve()
        for connection in psutil.net_connections(kind="tcp"):
            if connection.status != psutil.CONN_LISTEN or connection.laddr.port != 8081:
                continue
            if not connection.pid:
                raise RuntimeOperationError("Cannot identify the server on port 8081")
            process = psutil.Process(connection.pid)
            args = process.cmdline()
            model = args[args.index("-m") + 1] if "-m" in args else ""
            if (Path(process.exe()).resolve() != executable or not model
                    or not Path(model).resolve().is_relative_to((self.config.data_dir / "models").resolve())):
                raise RuntimeOperationError("Port 8081 belongs to an unmanaged server; stop it before loading a model")
            return process
        return None

    async def loaded_path(self):
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get("http://127.0.0.1:8081/props")
                response.raise_for_status()
                return str(response.json().get("model_path", ""))
        except (httpx.HTTPError, ValueError):
            return ""

    async def list(self):
        entries = await asyncio.to_thread(inventory, self.config.data_dir)
        loaded = await self.loaded_path()
        for entry in entries:
            entry["ready"] = bool(loaded) and Path(loaded).resolve() == Path(entry["location"])
            entry["status"] = "Loaded" if entry["ready"] else "Downloaded"
        return entries

    async def delete(self, model_path: str):
        async with self.lock:
            entries = await self.list()
            selected = next((item for item in entries if item["model_path"] == model_path), None)
            if selected is None:
                raise RuntimeOperationError("Select a downloaded GGUF from Alice's model library")
            if selected["ready"]:
                raise RuntimeOperationError("Load another model before deleting the loaded model")
            Path(selected["location"]).unlink()
            return {"deleted": True}

    async def load(self, model_path: str):
        async with self.lock:
            entries = await asyncio.to_thread(inventory, self.config.data_dir)
            selected = next((item for item in entries if item["model_path"] == model_path), None)
            if selected is None:
                raise RuntimeOperationError("Select a downloaded GGUF from Alice's model library")
            executable = llama_cpp_executable()
            if not executable.is_file():
                raise RuntimeOperationError("The bundled llama.cpp server is missing")
            target = Path(selected["location"])
            with target.open("rb") as source:
                if source.read(4) != b"GGUF":
                    raise RuntimeOperationError("This file is not a GGUF model")
            distributed = self.distributed.get()
            if self.bridges:
                distributed = await self.bridges.resolve(distributed)
            if distributed.enabled:
                try:
                    await probe_devices(executable, distributed)
                except TimeoutError as error:
                    raise RuntimeOperationError("GPU worker discovery timed out; the existing model was left running") from error
            try:
                loaded = await self.loaded_path()
                process = await asyncio.to_thread(self.owned_listener)
                matches = loaded == str(target) and process is not None and matches_settings(process.cmdline(), distributed)
            except psutil.Error as error:
                raise RuntimeOperationError("Cannot inspect the running model server; check process permissions") from error
            if not matches:
                if process:
                    process.terminate()
                    try:
                        await asyncio.to_thread(process.wait, timeout=20)
                    except psutil.TimeoutExpired as error:
                        raise RuntimeOperationError("The previous model server did not stop; retry after it exits") from error
                logs = self.config.data_dir / "logs"
                logs.mkdir(exist_ok=True)
                with (logs / "model-loader.log").open("ab") as output:
                    child = subprocess.Popen(
                        [str(executable), "-m", str(target), "--alias", selected["name"],
                         "--host", "127.0.0.1", "--port", "8081", "-c", "4096",
                         "-ngl", "99", "-np", "1", *distributed.arguments()],
                        stdout=output, stderr=output, stdin=subprocess.DEVNULL,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                try:
                    async with httpx.AsyncClient(timeout=2) as client:
                        for _ in range(1800 if distributed.enabled else 180):
                            if child.poll() is not None:
                                raise RuntimeOperationError("Model failed to load; see logs/model-loader.log (the model may be unsupported or exceed available memory)")
                            try:
                                response = await client.get("http://127.0.0.1:8081/health")
                                if response.status_code == 200:
                                    break
                            except httpx.HTTPError:
                                pass
                            await asyncio.sleep(1)
                        else:
                            raise RuntimeOperationError("Model loading timed out; see logs/model-loader.log")
                except BaseException:
                    if child.poll() is None:
                        child.terminate()
                        await asyncio.to_thread(child.wait)
                    raise
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get("http://127.0.0.1:8081/v1/models")
                response.raise_for_status()
                model_id = response.json()["data"][0]["id"]
            saved = self.config.data_dir / "loaded-model.txt"
            saved.write_text(str(target), encoding="utf-8")
            self.config.upsert_provider(ProviderProfile(
                id="llama_cpp_local", name="llama.cpp (Alice managed)", kind="openai",
                base_url="http://127.0.0.1:8081/v1", default_model=model_id,
            ))
            self.config.set_active("llama_cpp_local")
            self.config.set_active_model(model_id)
            return {"model": model_id, "provider_id": "llama_cpp_local", "status": "Loaded"}
