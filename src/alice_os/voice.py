from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class VoiceError(RuntimeError):
    pass


REFERENCE_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
WINDOWS_FEMALE_SPEAKER = "WINDOWS-ZIRA"
OPENVOICE_FEMALE_SPEAKER = "OPENVOICE-FEMALE"
OPENVOICE_WORKER_PORT = 7791
_openvoice_worker: asyncio.subprocess.Process | None = None
_openvoice_request_lock: asyncio.Lock | None = None


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


async def synthesize_openvoice(
    *, data_dir: Path, text: str, speaker: str = OPENVOICE_FEMALE_SPEAKER, speed: float = 1.0, reference: str = ""
) -> dict[str, str]:
    return await _synthesize_openvoice(
        data_dir=data_dir, text=text, speaker=speaker, speed=speed, reference=reference
    )


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
            str(_openvoice_python(root)), str(worker), "--openvoice-root", str(root),
            creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    for _ in range(80):
        await asyncio.sleep(0.25)
        try:
            await asyncio.to_thread(_worker_request, "/health")
            return
        except VoiceError:
            continue
    raise VoiceError("OpenVoice worker did not finish starting. Try the voice test again in a moment.")


def _openvoice_lock() -> asyncio.Lock:
    global _openvoice_request_lock
    if _openvoice_request_lock is None:
        _openvoice_request_lock = asyncio.Lock()
    return _openvoice_request_lock


async def _synthesize_openvoice(
    *, data_dir: Path, text: str, speaker: str, speed: float = 1.0, reference: str = ""
) -> dict[str, str]:
    clean_text = " ".join(text.split())
    if not clean_text:
        raise VoiceError("Enter text for Alice to speak.")
    if len(clean_text) > 8_000:
        raise VoiceError("Voice output is limited to 8,000 characters at a time.")

    output_dir = data_dir / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"alice-{uuid.uuid4().hex}.wav"
    output = output_dir / filename

    if speaker == WINDOWS_FEMALE_SPEAKER:
        if reference:
            raise VoiceError("Voice references use OpenVoice. Select OpenVoice English before using a reference recording.")
        return await _synthesize_windows_female(clean_text, speed, output, filename)

    if speaker == OPENVOICE_FEMALE_SPEAKER:
        reference_path = _alice_female_reference(data_dir)
        if not reference_path.is_file():
            raise VoiceError("Alice's OpenVoice female reference is missing. Run the OpenVoice setup again.")
        speaker = "EN-Newest"
    else:
        reference_path = _reference_path(data_dir, reference)

    status = openvoice_status()
    if not status["ready"]:
        raise VoiceError(f"OpenVoice is not ready: {status['message']}")
    root = Path(status["root"])
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
        "output": str(output),
    }
    if reference_path:
        worker_payload["reference"] = str(reference_path)
        worker_payload["embedding_cache"] = str(_embedding_cache_path(data_dir, reference_path))
    async with _openvoice_lock():
        try:
            await _ensure_openvoice_worker(root)
            await asyncio.to_thread(_worker_request, "/synthesize", worker_payload, 120)
            if output.is_file():
                return {"url": f"/audio/{filename}", "filename": filename}
        except VoiceError:
            # Preserve the one-shot runner as a recovery path if the persistent worker cannot start.
            pass
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
    except TimeoutError as error:
        process.kill()
        await process.wait()
        raise VoiceError("OpenVoice took longer than five minutes and was stopped.") from error
    if process.returncode != 0 or not output.is_file():
        detail = stderr.decode("utf-8", errors="replace").strip()[-800:]
        raise VoiceError(detail or "OpenVoice could not create an audio reply.")
    return {"url": f"/audio/{filename}", "filename": filename}


async def _synthesize_windows_female(text: str, speed: float, output: Path, filename: str) -> dict[str, str]:
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
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
    except TimeoutError as error:
        process.kill()
        await process.wait()
        raise VoiceError("The Windows voice took longer than one minute and was stopped.") from error
    if process.returncode != 0 or not output.is_file():
        detail = stderr.decode("utf-8", errors="replace").strip()[-800:]
        raise VoiceError(detail or "Windows could not create the female voice reply.")
    return {"url": f"/audio/{filename}", "filename": filename}
