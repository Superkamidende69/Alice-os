"""One inventory for local GGUF files and ownership-checked runtime switching."""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import httpx
import psutil

from .distributed import DistributedStore, matches_settings, probe_devices
from .models import ProviderProfile
from .paths import resource_root
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
    hf_root = root / "huggingface"
    for directory in sorted(hf_root.iterdir()) if hf_root.is_dir() else []:
        if not directory.is_dir() or not directory.resolve().is_relative_to(root):
            continue
        weights = [p for p in directory.rglob("*.safetensors")
                   if ".cache" not in p.parts and p.resolve().is_relative_to(root)]
        if not weights:
            continue
        config = {}
        config_path = directory / "config.json"
        try:
            if config_path.resolve().is_relative_to(root) and config_path.stat().st_size < 1024 * 1024:
                config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        model_type = config.get("model_type", "") if isinstance(config, dict) else ""
        companion = model_type == "gemma4_assistant"
        janus = model_type == "janus" and directory.name == "deepseek-community--Janus-Pro-1B"
        reason = ("This is a Gemma 4 speculative-decoding draft companion, not a standalone chat model. "
                  "It requires the matching Gemma 4 target model and a runtime that supports the pair."
                  if companion else "Safetensors files are saved locally. Alice's managed loader supports GGUF; "
                  "this repository needs a compatible external runtime. Downloaded files may be incomplete.")
        relative = directory.resolve().relative_to(root).as_posix()
        if janus:
            reason = "Janus Pro local text chat. Uses the dedicated CUDA runtime; image requests and workspace tools are not supported by this endpoint."
        size = sum(p.stat().st_size for p in weights)
        entries.append({
            "id": relative, "model_path": relative, "name": directory.name.replace("--", "/"),
            "location": str(directory.resolve()), "size": size, "model_size_bytes": size,
            "size_source": "Local weight files", "format": "Safetensors", "backend": "transformers",
            "installed": True, "ready": False, "loadable": janus, "source": "Hugging Face",
            "runtime": "janus" if janus else "unsupported",
            "status": "Ready to start (text chat)" if janus else "Companion model — target required" if companion else "Files present — runtime required",
            "description": reason, "compatibility_message": reason,
        })
    return entries


class ModelManager:
    def __init__(self, config):
        self.config = config
        self.lock = asyncio.Lock()
        self.distributed = DistributedStore(config.data_dir)
        self.bridges = None
        self.janus_process = None

    async def janus_ready(self, directory):
        try:
            async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
                response = await client.get("http://127.0.0.1:8082/health")
                value = response.json()
                return value.get("service") == "alice-janus" and Path(value.get("model_dir", "")).resolve() == Path(directory).resolve()
        except (httpx.HTTPError, ValueError):
            return False

    async def stop_janus(self):
        async with self.lock:
            expected_python = (resource_root() / ".venv-janus/Scripts/python.exe").resolve()
            expected_script = (resource_root() / "scripts/janus-server.py").resolve()
            for connection in psutil.net_connections(kind="tcp"):
                if connection.status != psutil.CONN_LISTEN or connection.laddr.port != 8082 or not connection.pid:
                    continue
                process = psutil.Process(connection.pid)
                args = process.cmdline()
                parent = process.parent()
                owned_executable = Path(process.exe()).resolve() == expected_python or (
                    parent is not None and Path(parent.exe()).resolve() == expected_python)
                if not owned_executable or len(args) < 2 or Path(args[0]).resolve() != expected_python or Path(args[1]).resolve() != expected_script:
                    raise RuntimeOperationError("Port 8082 is not owned by Alice's Janus service; nothing was stopped")
                if "--model-dir" not in args or not Path(args[args.index("--model-dir") + 1]).resolve().is_relative_to((self.config.data_dir / "models").resolve()):
                    raise RuntimeOperationError("Janus belongs to another Alice data directory; nothing was stopped")
                process.terminate()
                await asyncio.to_thread(process.wait, timeout=20)
                return {"stopped": True}
            return {"stopped": False}

    async def load_janus(self, selected):
        if not await self.janus_ready(selected["location"]):
            python = resource_root() / ".venv-janus/Scripts/python.exe"
            script = resource_root() / "scripts/janus-server.py"
            if not python.is_file() or not script.is_file():
                raise RuntimeOperationError("Install the dedicated Janus runtime first; see docs/janus-local.md")
            if any(c.status == psutil.CONN_LISTEN and c.laddr.port == 8082 for c in psutil.net_connections(kind="tcp")):
                raise RuntimeOperationError("Port 8082 is occupied; no existing service was stopped")
            logs = self.config.data_dir / "logs"
            logs.mkdir(exist_ok=True)
            with (logs / "janus-server.log").open("ab") as output:
                self.janus_process = subprocess.Popen([str(python), str(script), "--model-dir", selected["location"]],
                    stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            for _ in range(600):
                if self.janus_process.poll() is not None:
                    raise RuntimeOperationError("Janus failed to start; see logs/janus-server.log")
                if await self.janus_ready(selected["location"]):
                    break
                await asyncio.sleep(1)
            else:
                # Windows venv launchers have a separate interpreter child.
                # Reap only descendants of the process we created.
                children = psutil.Process(self.janus_process.pid).children(recursive=True)
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                self.janus_process.terminate()
                await asyncio.to_thread(self.janus_process.wait)
                raise RuntimeOperationError("Janus startup timed out; see logs/janus-server.log")
        self.config.upsert_provider(ProviderProfile(id="janus_local", name="Janus Pro · local text chat", kind="openai",
            base_url="http://127.0.0.1:8082/v1", default_model="Janus-Pro-1B"))
        self.config.set_active("janus_local")
        self.config.set_active_model("Janus-Pro-1B")
        return {"model": "Janus-Pro-1B", "provider_id": "janus_local", "status": "Loaded"}

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
            if entry.get("runtime") == "janus":
                entry["ready"] = await self.janus_ready(entry["location"])
                entry["status"] = "Loaded (text chat)" if entry["ready"] else "Ready to start (text chat)"
                continue
            if entry.get("loadable") is False:
                continue
            entry["ready"] = bool(loaded) and Path(loaded).resolve() == Path(entry["location"])
            entry["status"] = "Loaded" if entry["ready"] else "Downloaded"
        return entries

    async def delete(self, model_path: str):
        async with self.lock:
            entries = await self.list()
            selected = next((item for item in entries if item["model_path"] == model_path), None)
            if selected is None or selected.get("format") != "GGUF":
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
            if selected.get("loadable") is False:
                raise RuntimeOperationError(selected["compatibility_message"])
            if selected.get("runtime") == "janus":
                return await self.load_janus(selected)
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
