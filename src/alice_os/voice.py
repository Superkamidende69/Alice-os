from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class VoiceError(RuntimeError):
    pass


class VoiceInterrupted(VoiceError):
    pass


class VoiceCancellation:
    """A cooperative cancellation marker shared with the isolated TTS runtime."""

    def __init__(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="alice-voice-job-")
        self.path = Path(self.directory.name) / "cancelled"
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True
        self.path.touch()

    def check(self) -> None:
        if self.cancelled:
            raise VoiceInterrupted("Speech was interrupted.")

    def close(self) -> None:
        self.directory.cleanup()


REFERENCE_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
WINDOWS_FEMALE_SPEAKER = "WINDOWS-ZIRA"
OPENVOICE_FEMALE_SPEAKER = "OPENVOICE-FEMALE"
OPENVOICE_WORKER_PORT = 7791
VOICE_STYLE_PRESETS: dict[str, dict[str, float]] = {
    "balanced": {"noise_scale": 0.60, "noise_scale_w": 0.80, "sdp_ratio": 0.20},
    "calm": {"noise_scale": 0.42, "noise_scale_w": 0.56, "sdp_ratio": 0.10},
    "warm": {"noise_scale": 0.52, "noise_scale_w": 0.66, "sdp_ratio": 0.16},
    "confident": {"noise_scale": 0.54, "noise_scale_w": 0.72, "sdp_ratio": 0.24},
    "upbeat": {"noise_scale": 0.72, "noise_scale_w": 0.96, "sdp_ratio": 0.36},
    "playful": {"noise_scale": 0.82, "noise_scale_w": 1.04, "sdp_ratio": 0.42},
    "serious": {"noise_scale": 0.40, "noise_scale_w": 0.54, "sdp_ratio": 0.10},
    "dramatic": {"noise_scale": 0.86, "noise_scale_w": 1.08, "sdp_ratio": 0.48},
}
_openvoice_worker: asyncio.subprocess.Process | None = None
_openvoice_request_lock: asyncio.Lock | None = None
_openvoice_start_lock: asyncio.Lock | None = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _openvoice_root() -> Path:
    override = os.environ.get("OPENVOICE_HOME", "").strip()
    return Path(override).expanduser().resolve() if override else _project_root() / "tools" / "OpenVoice"


def _openvoice_python(root: Path) -> Path:
    return root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def openvoice_status() -> dict[str, Any]:
    root = _openvoice_root()
    python = _openvoice_python(root)
    checkpoints = root / "checkpoints_v2" / "converter" / "checkpoint.pth"
    installed = root.is_dir()
    ready = installed and python.is_file() and checkpoints.is_file()
    if ready:
        message = "Ready for local speech and voice cloning."
    elif not installed:
        message = "OpenVoice source is not installed."
    elif not python.is_file():
        message = "OpenVoice needs its isolated Python 3.10 environment."
    else:
        message = "OpenVoice checkpoints still need to be downloaded."
    return {
        "installed": installed,
        "ready": ready,
        "root": str(root),
        "message": message,
    }


def voice_pipeline_status() -> dict[str, Any]:
    """Describe Alice's single-process voice path in LocalAI-compatible terms.

    The browser owns transcription today because Web Speech is available without
    downloading another model. VAD, the LLM stream, and local OpenVoice synthesis
    are Alice-owned services and remain on the Alice host.
    """
    runtime = openvoice_status()
    return {
        "name": "Alice voice pipeline",
        "stages": [
            {
                "id": "vad",
                "name": "Voice activity detection",
                "engine": "WebRTC VAD",
                "transport": "Alice WebSocket",
                "ready": True,
                "streaming": True,
            },
            {
                "id": "transcription",
                "name": "Speech transcription",
                "engine": "Browser Web Speech API",
                "transport": "Browser microphone",
                "ready": "client",
                "streaming": True,
                "local": False,
            },
            {
                "id": "llm",
                "name": "Alice language model",
                "engine": "Active Alice provider",
                "transport": "Alice SSE",
                "ready": True,
                "streaming": True,
            },
            {
                "id": "tts",
                "name": "Speech synthesis",
                "engine": "OpenVoice / MeloTTS",
                "transport": "Alice local worker",
                "ready": runtime["ready"],
                "streaming": True,
                "local": True,
            },
        ],
        "streaming": {
            "llm": True,
            "tts": True,
            "transcription": True,
            "clause_chunking": True,
        },
        "transcription_note": (
            "Dictation currently uses the browser speech recognizer. A local Whisper stage "
            "can be enabled later when its model is installed."
        ),
    }


async def synthesize_openvoice(
    *,
    data_dir: Path,
    text: str,
    speaker: str = OPENVOICE_FEMALE_SPEAKER,
    speed: float = 1.0,
    reference: str = "",
    style: str = "balanced",
    noise_scale: float | None = None,
    noise_scale_w: float | None = None,
    sdp_ratio: float | None = None,
    cancellation: VoiceCancellation | None = None,
) -> dict[str, bytes]:
    return await _synthesize_openvoice(
        data_dir=data_dir,
        text=text,
        speaker=speaker,
        speed=speed,
        reference=reference,
        style=style,
        noise_scale=noise_scale,
        noise_scale_w=noise_scale_w,
        sdp_ratio=sdp_ratio,
        cancellation=cancellation,
    )


def resolve_voice_style(
    style: str, noise_scale: float | None, noise_scale_w: float | None, sdp_ratio: float | None
) -> dict[str, float]:
    try:
        preset = VOICE_STYLE_PRESETS[style]
    except KeyError as error:
        raise VoiceError(f"Unknown voice style: {style}") from error
    return {
        "noise_scale": preset["noise_scale"] if noise_scale is None else noise_scale,
        "noise_scale_w": preset["noise_scale_w"] if noise_scale_w is None else noise_scale_w,
        "sdp_ratio": preset["sdp_ratio"] if sdp_ratio is None else sdp_ratio,
    }


async def warm_openvoice() -> dict[str, Any]:
    """Start the persistent OpenVoice worker before an answer is ready to speak."""
    status = openvoice_status()
    if not status["ready"]:
        return {**status, "warmed": False}
    root = Path(status["root"])
    await _ensure_openvoice_worker(root)
    await asyncio.to_thread(_worker_request, "/warm")
    return {**status, "warmed": True}


def list_voice_references(data_dir: Path) -> list[dict[str, str | int]]:
    directory = data_dir / "voice" / "references"
    if not directory.is_dir():
        return []
    entries = []
    for path in directory.iterdir():
        if path.is_file() and path.suffix.casefold() in REFERENCE_SUFFIXES:
            stem = re.sub(r"^[0-9a-f]{8}-", "", path.stem)
            if re.fullmatch(r"alice-[0-9a-f]{16,}", stem):
                label = "Alice voice sample"
            elif stem.startswith("alice-"):
                label = f"Alice reference {stem.removeprefix('alice-')}"
            else:
                label = stem.replace("-", " ")
            entries.append({"name": path.name, "label": label, "size": path.stat().st_size})
    return sorted(entries, key=lambda entry: str(entry["name"]).casefold())


def save_voice_reference(*, data_dir: Path, filename: str, content: bytes) -> dict[str, str | int]:
    suffix = Path(filename).suffix.casefold()
    if suffix not in REFERENCE_SUFFIXES:
        raise VoiceError("Use a WAV, MP3, M4A, FLAC, or OGG reference recording.")
    if not content or len(content) > 25 * 1024 * 1024:
        raise VoiceError("Reference recordings must be between 1 byte and 25 MiB.")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(filename).stem).strip(".-") or "reference"
    target_dir = data_dir / "voice" / "references"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid.uuid4().hex[:8]}-{stem[:80]}{suffix}"
    target.write_bytes(content)
    return {"name": target.name, "size": target.stat().st_size}


def remove_voice_reference(*, data_dir: Path, name: str) -> None:
    path = _reference_path(data_dir, name)
    if path is None:
        raise VoiceError("Choose a saved reference recording to remove.")
    _embedding_cache_path(data_dir, path).unlink(missing_ok=True)
    path.unlink()


def _reference_path(data_dir: Path, name: str) -> Path | None:
    if not name:
        return None
    candidate = Path(name)
    if candidate.name != name or candidate.suffix.casefold() not in REFERENCE_SUFFIXES:
        raise VoiceError("The selected reference recording is not valid.")
    path = data_dir / "voice" / "references" / candidate.name
    if not path.is_file():
        raise VoiceError("The selected reference recording was not found.")
    return path


def _alice_female_reference(data_dir: Path) -> Path:
    return data_dir / "voice" / "system" / "alice-female-zira-reference.wav"


def _embedding_cache_path(data_dir: Path, reference: Path) -> Path:
    stat = reference.stat()
    digest = hashlib.sha256(f"{reference.resolve()}:{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()[:20]
    return data_dir / "voice" / "embedding-cache" / f"{digest}.pth"


def _worker_request(path: str, payload: dict[str, Any] | None = None, timeout: float = 5) -> dict[str, Any]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        f"http://127.0.0.1:{OPENVOICE_WORKER_PORT}{path}", data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 -- fixed loopback URL
            return json.loads(response.read().decode())
    except HTTPError as error:
        detail = error.read().decode(errors="replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except json.JSONDecodeError:
            pass
        raise VoiceError(str(detail)) from error
    except (OSError, TimeoutError, URLError) as error:
        raise VoiceError("OpenVoice worker is not running.") from error


async def _ensure_openvoice_worker(root: Path) -> None:
    global _openvoice_start_lock
    if _openvoice_start_lock is None:
        _openvoice_start_lock = asyncio.Lock()
    async with _openvoice_start_lock:
        await _start_openvoice_worker(root)


async def _stop_voice_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    if os.name == "nt":
        # Windows venv launchers spawn another Python process. Killing just the
        # launcher leaves inference running and stdout pipes open indefinitely.
        killer = await asyncio.create_subprocess_exec(
            "taskkill", "/PID", str(process.pid), "/T", "/F",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000,
        )
        await killer.wait()
    else:
        process.kill()
    await process.wait()


async def _start_openvoice_worker(root: Path) -> None:
    global _openvoice_worker
    try:
        await asyncio.to_thread(_worker_request, "/health")
        return
    except VoiceError:
        pass
    if _openvoice_worker is None or _openvoice_worker.returncode is not None:
        worker = _project_root() / "scripts" / "openvoice_worker.py"
        flags = 0x08000000 if os.name == "nt" else 0
        _openvoice_worker = await asyncio.create_subprocess_exec(
            str(_openvoice_python(root)), str(worker), "--openvoice-root", str(root), "--port", str(OPENVOICE_WORKER_PORT),
            creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    deadline = asyncio.get_running_loop().time() + 300
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.25)
        if _openvoice_worker is not None and _openvoice_worker.returncode is not None:
            raise VoiceError("OpenVoice worker exited during startup.")
        try:
            await asyncio.to_thread(_worker_request, "/health", None, 1)
            return
        except VoiceError:
            continue
    if _openvoice_worker is not None:
        await _stop_voice_process(_openvoice_worker)
    raise VoiceError("OpenVoice worker did not finish starting within five minutes.")


def _openvoice_lock() -> asyncio.Lock:
    global _openvoice_request_lock
    if _openvoice_request_lock is None:
        _openvoice_request_lock = asyncio.Lock()
    return _openvoice_request_lock


async def _synthesize_openvoice(
    *,
    data_dir: Path,
    text: str,
    speaker: str,
    speed: float = 1.0,
    reference: str = "",
    style: str = "balanced",
    noise_scale: float | None = None,
    noise_scale_w: float | None = None,
    sdp_ratio: float | None = None,
    cancellation: VoiceCancellation | None = None,
) -> dict[str, bytes]:
    if cancellation:
        cancellation.check()
    clean_text = " ".join(text.split())
    if not clean_text:
        raise VoiceError("Enter text for Alice to speak.")
    if len(clean_text) > 8_000:
        raise VoiceError("Voice output is limited to 8,000 characters at a time.")

    prosody = resolve_voice_style(style, noise_scale, noise_scale_w, sdp_ratio)

    if speaker == WINDOWS_FEMALE_SPEAKER:
        if reference:
            raise VoiceError("Voice references use OpenVoice. Select OpenVoice English before using a reference recording.")
        with tempfile.NamedTemporaryFile(prefix="alice-", suffix=".wav", delete=False) as temporary:
            output = Path(temporary.name)
        try:
            return await _synthesize_windows_female(clean_text, speed, output, cancellation)
        finally:
            output.unlink(missing_ok=True)

    if speaker == OPENVOICE_FEMALE_SPEAKER:
        reference_path = _reference_path(data_dir, reference) if reference else _alice_female_reference(data_dir)
        if not reference_path.is_file():
            raise VoiceError("Alice's OpenVoice female reference is missing. Run the OpenVoice setup again.")
        speaker = "EN-Newest"
    else:
        reference_path = _reference_path(data_dir, reference)

    status = openvoice_status()
    if not status["ready"]:
        raise VoiceError(f"OpenVoice is not ready: {status['message']}")
    root = Path(status["root"])
    with tempfile.NamedTemporaryFile(prefix="alice-", suffix=".wav", delete=False) as temporary:
        output = Path(temporary.name)
    runner = _project_root() / "scripts" / "openvoice_speak.py"
    command = [
        str(_openvoice_python(root)),
        str(runner),
        "--openvoice-root",
        str(root),
        "--text",
        clean_text,
        "--speaker",
        speaker,
        "--speed",
        str(speed),
        "--noise-scale",
        str(prosody["noise_scale"]),
        "--noise-scale-w",
        str(prosody["noise_scale_w"]),
        "--sdp-ratio",
        str(prosody["sdp_ratio"]),
        "--output",
        str(output),
    ]
    if reference_path:
        command.extend(
            ["--reference", str(reference_path), "--embedding-cache", str(_embedding_cache_path(data_dir, reference_path))]
        )
    worker_payload: dict[str, Any] = {
        "text": clean_text,
        "speaker": speaker,
        "speed": speed,
        **prosody,
        "output": str(output),
    }
    if reference_path:
        worker_payload["reference"] = str(reference_path)
        worker_payload["embedding_cache"] = str(_embedding_cache_path(data_dir, reference_path))
    if cancellation:
        worker_payload["cancel_path"] = str(cancellation.path)
        command.extend(["--cancel-path", str(cancellation.path)])
    try:
        async with _openvoice_lock():
            if cancellation:
                cancellation.check()
            try:
                await _ensure_openvoice_worker(root)
            except VoiceError:
                # Only retry startup failures, never duplicate an in-flight inference.
                await _run_voice_process(command, cancellation, timeout=300)
            else:
                if cancellation:
                    cancellation.check()
                try:
                    request = asyncio.create_task(
                        asyncio.to_thread(_worker_request, "/synthesize", worker_payload, 300)
                    )
                    try:
                        await asyncio.shield(request)
                    except asyncio.CancelledError:
                        if cancellation:
                            cancellation.cancel()
                        # Keep the marker and output alive until the worker has
                        # reached its checkpoint, even when the HTTP task exits.
                        try:
                            await request
                        except VoiceError:
                            pass
                        raise
                except VoiceError:
                    if cancellation:
                        cancellation.check()
                    raise
            if cancellation:
                cancellation.check()
            if not output.is_file() or not output.stat().st_size:
                raise VoiceError("OpenVoice could not create an audio reply.")
            return {"audio": await asyncio.to_thread(output.read_bytes)}
    finally:
        output.unlink(missing_ok=True)


async def _run_voice_process(
    command: list[str], cancellation: VoiceCancellation | None, *, timeout: float
) -> None:
    if cancellation:
        cancellation.check()
    flags = 0x08000000 if os.name == "nt" else 0
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        creationflags=flags,
    )
    communication = asyncio.create_task(process.communicate())
    try:
        async with asyncio.timeout(timeout):
            while not communication.done():
                if cancellation:
                    cancellation.check()
                await asyncio.wait({communication}, timeout=0.05)
            _, stderr = await communication
        if cancellation:
            cancellation.check()
        if process.returncode:
            detail = stderr.decode("utf-8", errors="replace").strip()[-800:]
            raise VoiceError(detail or "Voice synthesis failed.")
    except TimeoutError as error:
        raise VoiceError("Voice synthesis timed out.") from error
    finally:
        if process.returncode is None:
            await _stop_voice_process(process)
        await communication


async def _synthesize_windows_female(
    text: str, speed: float, output: Path, cancellation: VoiceCancellation | None = None
) -> dict[str, bytes]:
    if os.name != "nt":
        raise VoiceError("The built-in female voice is available on Windows only. Select OpenVoice English instead.")
    script = _project_root() / "scripts" / "windows_female_speak.ps1"
    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Text",
        text,
        "-Output",
        str(output),
        "-Speed",
        str(speed),
    ]
    await _run_voice_process(command, cancellation, timeout=60)
    if not output.is_file() or not output.stat().st_size:
        raise VoiceError("Windows could not create the female voice reply.")
    return {"audio": await asyncio.to_thread(output.read_bytes)}
