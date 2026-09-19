"""Optional resident CPU TTS, isolated from the main Python environment."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .paths import bundled, resource_root

VOICES = {"KOKORO-HEART": "af_heart", "KOKORO-BELLA": "af_bella", "KOKORO-MICHAEL": "am_michael"}
_process = None
_lock = None
_loop = None


def root() -> Path:
    base = Path(sys.executable).parent if bundled() else resource_root()
    return Path(os.environ.get("ALICE_KOKORO_HOME", str(base / "tools/kokoro")))


def status() -> dict:
    directory = root()
    python = directory / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    ready = python.is_file() and all((directory / name).is_file() for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"))
    return {"ready": ready, "python": str(python), "engine": "Kokoro · local CPU", "voices": list(VOICES)}


def _stop():
    global _process
    process, _process = _process, None
    if process is not None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for stream in (process.stdin, process.stdout):
            if stream:
                stream.close()


def _request(payload, data_dir, stopped):
    global _process
    if stopped.is_set():
        return
    if _process is None or _process.poll() is not None:
        _stop()
        log = data_dir / "logs/kokoro.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("ab") as output:
            _process = subprocess.Popen(
                [status()["python"], "-u", str(resource_root() / "scripts/kokoro_worker.py"), str(root())],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=output, text=True, encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
    if stopped.is_set():
        _process.terminate()
        return
    _process.stdin.write(json.dumps(payload) + "\n")
    _process.stdin.flush()
    result = _process.stdout.readline()
    if not result:
        raise RuntimeError("Kokoro worker stopped. Check logs/kokoro.log.")
    result = json.loads(result)
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Kokoro speech failed"))


def lock():
    global _lock, _loop
    loop = asyncio.get_running_loop()
    if _loop is not loop:
        _loop, _lock = loop, asyncio.Lock()
    return _lock


async def synthesize(text, speaker, speed, data_dir, cancellation=None):
    if speaker not in VOICES:
        raise RuntimeError("Unknown Kokoro voice")
    if not status()["ready"]:
        raise RuntimeError("Kokoro is not installed. Run scripts/setup-kokoro.py first.")
    async with lock():
        if cancellation:
            cancellation.check()
        with tempfile.TemporaryDirectory(prefix="alice-kokoro-") as directory:
            output = Path(directory) / "speech.wav"
            stopped = threading.Event()
            request = asyncio.create_task(asyncio.to_thread(_request, {
                "text": text, "voice": VOICES[speaker], "speed": speed, "output": str(output),
            }, data_dir, stopped))
            try:
                async with asyncio.timeout(120):
                    while not request.done():
                        if cancellation:
                            cancellation.check()
                        await asyncio.sleep(.05)
                    await request
                if cancellation:
                    cancellation.check()
                return {"audio": output.read_bytes()}
            except BaseException:
                # Killing inference also releases a blocked readline. Wait before
                # deleting its output or starting another request.
                stopped.set()
                if _process is not None and _process.poll() is None:
                    _process.terminate()
                await asyncio.gather(request, return_exceptions=True)
                await asyncio.to_thread(_stop)
                raise


async def shutdown():
    async with lock():
        await asyncio.to_thread(_stop)
