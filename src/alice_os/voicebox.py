"""Local Voicebox REST adapter. Alice owns playback and only cancels its own jobs."""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import httpx
import psutil

from .paths import bundled, resource_root

PREFIX = "VOICEBOX:"
MAX_AUDIO = 30 * 1024 * 1024
ENGINES = {"qwen", "qwen_custom_voice", "luxtts", "chatterbox", "chatterbox_turbo", "tada", "kokoro"}


def base_url() -> str:
    value = os.environ.get("ALICE_VOICEBOX_URL", "http://127.0.0.1:17493").rstrip("/")
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise ValueError("ALICE_VOICEBOX_URL must be a loopback HTTP URL without a path.")
    port = parsed.port or 80
    host = "[::1]" if parsed.hostname == "::1" else "127.0.0.1"
    return f"http://{host}:{port}"


def client(timeout=5):
    return httpx.AsyncClient(base_url=base_url(), timeout=timeout, trust_env=False, follow_redirects=False)


def identifier(value: str) -> str:
    return str(UUID(value))


def runtime_root() -> Path:
    root = Path(sys.executable).parent if bundled() else resource_root()
    return Path(os.environ.get("ALICE_VOICEBOX_HOME", str(root / "tools/voicebox-runtime")))


def executable() -> Path | None:
    return next((runtime_root() / "app").rglob("voicebox-server*.exe"), None)


async def status() -> dict:
    result = {"ready": False, "profiles": [], "installed": executable() is not None}
    try:
        async with client(3) as http:
            identity = await http.get("/")
            identity.raise_for_status()
            if "voicebox" not in str(identity.json().get("message", "")).lower():
                raise ValueError("The local service is not the Voicebox API.")
            response = await http.get("/profiles")
            response.raise_for_status()
            profiles = response.json()
            if not isinstance(profiles, list):
                raise ValueError("Unexpected Voicebox profile response.")
            for profile in profiles[:256]:
                if profile.get("voice_type") == "import":
                    continue
                result["profiles"].append({
                    "id": identifier(profile["id"]), "name": str(profile["name"])[:100],
                    "engine": profile.get("default_engine") or profile.get("preset_engine") or "qwen",
                    "language": profile.get("language", "en"),
                })
            result.update(ready=True, version=identity.json().get("version"),
                          message="Voicebox connected. Choose a profile for Alice's replies.")
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        result["profiles"] = []
        result["message"] = "Voicebox is offline or incompatible. Start Voicebox, then refresh profiles."
    return result


async def synthesize(text: str, speaker: str, cancellation=None) -> dict[str, bytes]:
    from .voice import VoiceError

    job_id = None
    completed = False
    try:
        profile_id = identifier(speaker.removeprefix(PREFIX))
        async with client(15) as http:
            try:
                async with asyncio.timeout(180):
                    if cancellation:
                        cancellation.check()
                    response = await http.get(f"/profiles/{profile_id}")
                    response.raise_for_status()
                    profile = response.json()
                    engine = profile.get("default_engine") or profile.get("preset_engine") or "qwen"
                    if engine not in ENGINES:
                        raise VoiceError("This Voicebox profile uses an unsupported engine.")
                    if cancellation:
                        cancellation.check()
                    response = await http.post("/generate", json={
                        "text": text, "profile_id": profile_id, "engine": engine,
                        "language": profile.get("language", "en"), "personality": False,
                        "max_chunk_chars": 800,
                    })
                    response.raise_for_status()
                    generation = response.json()
                    job_id = identifier(generation["id"])
                    while True:
                        if cancellation:
                            cancellation.check()
                        state = generation.get("status")
                        if state == "completed":
                            break
                        if state in {"failed", "cancelled", "canceled"}:
                            raise VoiceError("Voicebox generation failed: " + str(generation.get("error") or state)[:500])
                        if state not in {"loading_model", "generating", "queued", "pending", "processing"}:
                            raise VoiceError("Voicebox returned an unknown generation state.")
                        await asyncio.sleep(.2)
                        response = await http.get(f"/history/{job_id}")
                        response.raise_for_status()
                        generation = response.json()
                    audio = bytearray()
                    async with http.stream("GET", f"/audio/{job_id}") as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes():
                            if cancellation:
                                cancellation.check()
                            audio.extend(chunk)
                            if len(audio) > MAX_AUDIO:
                                raise VoiceError("Voicebox audio exceeds Alice's 30 MB limit.")
                    if audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
                        raise VoiceError("Voicebox did not return WAV audio.")
                    if cancellation:
                        cancellation.check()
                    completed = True
                    return {"audio": bytes(audio)}
            finally:
                if job_id and not completed:
                    try:
                        await http.post(f"/generate/{job_id}/cancel", timeout=2)
                    except httpx.HTTPError:
                        pass
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError, TimeoutError) as error:
        raise VoiceError("Voicebox speech failed. Check that Voicebox is running and the selected model is ready.") from error


class Runtime:
    """Own only the optional private runtime started by this Alice instance."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.process = None
        self.lock = asyncio.Lock()

    async def open_studio(self) -> dict:
        if base_url() != "http://127.0.0.1:17493":
            raise ValueError("Open your Voicebox app manually when using a custom port.")
        state = await self.start()
        if not state["ready"]:
            raise ValueError(state["message"])
        server = executable()
        program = server.parent / "voicebox.exe" if server else None
        if program is None or not program.is_file():
            raise ValueError("Open your installed Voicebox desktop app to manage voices.")
        # The user explicitly requested the interactive studio, so show its window.
        subprocess.Popen([str(program)], cwd=program.parent)
        return {"message": "Voicebox Studio opened on the Alice host."}

    async def start(self) -> dict:
        async with self.lock:
            state = await status()
            if state["ready"]:
                return state
            program = executable()
            if program is None:
                raise ValueError("Run scripts/setup-voicebox.py with Alice's Python first, or start the Voicebox desktop app.")
            if self.process is None or self.process.poll() is not None:
                log = self.data_dir / "logs/voicebox.log"
                log.parent.mkdir(parents=True, exist_ok=True)
                parsed = urlsplit(base_url())
                env = {**os.environ, "VOICEBOX_MODELS_DIR": str(runtime_root() / "models")}
                with log.open("ab") as output:
                    self.process = subprocess.Popen(
                        [str(program), "--host", parsed.hostname, "--port", str(parsed.port),
                         "--data-dir", str(self.data_dir / "voicebox"), "--parent-pid", str(os.getpid())],
                        cwd=program.parent, env=env, stdout=output, stderr=output,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
            for _ in range(20):
                if self.process.poll() is not None:
                    raise ValueError("Voicebox stopped during startup. Check logs/voicebox.log.")
                await asyncio.sleep(.5)
                state = await status()
                if state["ready"]:
                    return state
            return {**state, "message": "Voicebox is still starting. Refresh profiles shortly."}

    async def stop(self):
        async with self.lock:
            process, self.process = self.process, None
            if process is not None and process.poll() is None:
                await asyncio.to_thread(self._stop_tree, process)

    @staticmethod
    def _stop_tree(process):
        # Windows PyInstaller has a bootloader parent and an inference child.
        try:
            children = psutil.Process(process.pid).children(recursive=True)
        except psutil.NoSuchProcess:
            children = []
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(children, timeout=5)
        for child in alive:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
