from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import tempfile
import uuid
from http.client import HTTPException
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .paths import bundled, resource_root


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
TRANSCRIPTION_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}
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
_openvoice_transcription_lock: asyncio.Lock | None = None
_openvoice_start_lock: asyncio.Lock | None = None


def _project_root() -> Path:
    return resource_root()


def _openvoice_root() -> Path:
    override = os.environ.get("OPENVOICE_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if bundled():
        from .config import default_data_dir
        return default_data_dir() / "runtimes" / "OpenVoice"
    return _project_root() / "tools" / "OpenVoice"


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

    Whisper runs in Alice's isolated OpenVoice runtime when the installer has
    downloaded its compact local model. Browser speech remains a graceful
    fallback for existing installations until that one-time download completes.
    """
    runtime = openvoice_status()
    transcription = transcription_status()
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
                "engine": f"faster-whisper ({whisper_model_name()}, INT8)",
                "transport": "Alice local worker",
                "ready": transcription["ready"],
                "streaming": True,
                "local": True,
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
        "transcription_note": transcription["message"],
    }


def _whisper_model_root(root: Path) -> Path:
    return root / "models" / "whisper"


def whisper_model_name() -> str:
    """Return a supported Whisper size from the environment."""
    name = os.environ.get("ALICE_WHISPER_MODEL", "base").strip().casefold()
    return name if name in {"tiny", "base", "small", "medium"} else "base"


def transcription_status() -> dict[str, Any]:
    root = _openvoice_root()
    model_root = _whisper_model_root(root)
    model_name = whisper_model_name()
    model_ready = any(model_root.glob(f"models--Systran--faster-whisper-{model_name}/snapshots/*/model.bin"))
    runtime_ready = openvoice_status()["ready"]
    ready = bool(runtime_ready and model_ready)
    return {
        "ready": ready,
        "model": model_name,
        "local": True,
        "message": (
            "Local Whisper dictation is ready; microphone audio stays on this Alice host."
            if ready else "Local Whisper model is not installed yet; browser dictation remains available."
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


async def voice_worker_status() -> dict[str, Any]:
    """Read worker health without starting the worker or loading its models."""
    try:
        return await asyncio.to_thread(_worker_request, "/health", None, 1)
    except VoiceError:
        return {"ready": False, "message": "Voice worker is not running."}


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
    await asyncio.to_thread(_worker_request, "/warm", {}, 300)
    return {**status, "warmed": True}


async def transcribe_openvoice_audio(
    *, filename: str, content: bytes,
    on_partial: Callable[[dict[str, str]], Awaitable[None]] | None = None,
) -> dict[str, str]:
    """Transcribe a short browser recording using Alice's local Whisper worker."""
    status = transcription_status()
    if not status["ready"]:
        raise VoiceError(str(status["message"]))
    suffix = Path(filename).suffix.casefold()
    if suffix not in TRANSCRIPTION_SUFFIXES:
        raise VoiceError("Use a WAV, MP3, M4A, FLAC, OGG, WebM, or MP4 recording.")
    if not content or len(content) > 25 * 1024 * 1024:
        raise VoiceError("Dictation recordings must be between 1 byte and 25 MiB.")
    with tempfile.NamedTemporaryFile(prefix="alice-dictation-", suffix=suffix, delete=False) as temporary:
        input_path = Path(temporary.name)
        temporary.write(content)
    try:
        root = _openvoice_root()
        payload = {
            "input": str(input_path),
            "model_dir": str(_whisper_model_root(root)),
            "model": whisper_model_name(),
            "stream": True,
        }
        # Whisper runs on CPU and has its own worker lock, so listening need not
        # wait for an in-flight TTS request to reach its next cancellation point.
        async with _transcription_lock():
            await _ensure_openvoice_worker(root)
            loop = asyncio.get_running_loop()
            events: asyncio.Queue[dict[str, Any] | BaseException | None] = asyncio.Queue()

            def receive(event: dict[str, Any]) -> None:
                loop.call_soon_threadsafe(events.put_nowait, event)

            def stream_request() -> None:
                try:
                    if on_partial is None:
                        receive({**_worker_request("/transcribe", {**payload, "stream": False}, 180), "final": True})
                    else:
                        _worker_stream_request("/transcribe", payload, receive, 180)
                    loop.call_soon_threadsafe(events.put_nowait, None)
                except BaseException as error:
                    loop.call_soon_threadsafe(events.put_nowait, error)

            request = asyncio.create_task(asyncio.to_thread(stream_request))
            try:
                result: dict[str, Any] = {}
                while True:
                    event = await events.get()
                    if event is None:
                        break
                    if isinstance(event, BaseException):
                        raise event
                    if event.get("final"):
                        result = event
                    elif on_partial and str(event.get("text", "")).strip():
                        await on_partial({"text": str(event["text"]), "language": str(event.get("language", ""))})
                await asyncio.shield(request)
            except BaseException:
                # Cancelling to_thread does not stop the worker. Keep its input
                # and transcription slot alive until it finishes, even if a
                # disconnected client cancels this task more than once.
                while not request.done():
                    try:
                        await asyncio.shield(request)
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        break
                if not request.cancelled():
                    request.exception()
                raise
        text = str(result.get("text", "")).strip()
        if not text:
            raise VoiceError("Alice could not detect speech in that recording.")
        return {"text": text, "language": str(result.get("language", ""))}
    finally:
        input_path.unlink(missing_ok=True)


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


def _worker_stream_request(
    path: str, payload: dict[str, Any], on_event: Callable[[dict[str, Any]], None], timeout: float = 180
) -> None:
    data = json.dumps(payload).encode()
    request = Request(
        f"http://127.0.0.1:{OPENVOICE_WORKER_PORT}{path}", data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        completed = False
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 -- fixed loopback URL
            while line := response.readline(65537):
                if len(line) > 65536:
                    raise VoiceError("Voice transcription event exceeded the size limit.")
                if line.strip():
                    event = json.loads(line.decode())
                    if not isinstance(event, dict) or not isinstance(event.get("text"), str):
                        raise VoiceError("Voice transcription returned an invalid event.")
                    if completed:
                        raise VoiceError("Voice transcription sent data after completion.")
                    completed = event.get("final") is True
                    on_event(event)
        if not completed:
            raise VoiceError("Voice transcription ended before its final result.")
    except HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise VoiceError(detail or "Voice transcription failed.") from error
    except (OSError, TimeoutError, URLError, HTTPException, ValueError) as error:
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


async def shutdown_openvoice() -> None:
    """Stop only the isolated worker launched by this Alice process."""
    global _openvoice_worker
    worker = _openvoice_worker
    if worker is not None:
        await _stop_voice_process(worker)
        _openvoice_worker = None


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
            "--idle-seconds", str(_voice_idle_seconds()),
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


def _voice_idle_seconds() -> int:
    """Return the worker keep-alive window, with a safe five-minute default."""
    try:
        return max(0, min(int(os.environ.get("ALICE_VOICE_IDLE_SECONDS", "300")), 86400))
    except ValueError:
        return 300


def _transcription_lock() -> asyncio.Lock:
    global _openvoice_transcription_lock
    if _openvoice_transcription_lock is None:
        _openvoice_transcription_lock = asyncio.Lock()
    return _openvoice_transcription_lock


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
