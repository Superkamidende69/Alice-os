from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import unicodedata
import uuid
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def add_ffmpeg_to_path() -> None:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return
    packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    for executable in packages.glob("Gyan.FFmpeg.Essentials*/**/bin/ffmpeg.exe"):
        os.environ["PATH"] = str(executable.parent) + os.pathsep + os.environ.get("PATH", "")
        return


def text_for_speech(text: str) -> str:
    """Turn a chat/Markdown reply into the conservative English text Melo expects."""
    replacements = str.maketrans(
        {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": ",",
            "\u2014": ",",
            "\u2026": "...",
        }
    )
    normalized = unicodedata.normalize("NFKC", text).translate(replacements)
    # Markdown markers and symbols can create an empty phoneme group in Melo's
    # English tokenizer (notably a leading # heading). Keep only prose marks.
    prose = "".join(
        char
        for char in normalized
        if unicodedata.category(char) not in {"So", "Sk", "Cs", "Cc"}
    )
    prose = re.sub(r"[^A-Za-z0-9\s.,!?;:'\"()\-]", " ", prose)
    prose = re.sub(r"\s+", " ", prose).strip()
    return prose.lstrip(".,!?;:- ")


def speech_chunks(text: str, limit: int = 320) -> list[str]:
    chunks: list[str] = []
    current = ""
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split()
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > limit:
                chunks.append(current)
                current = word
            else:
                current = candidate
            if current.endswith((".", "!", "?")) and len(current) >= 120:
                chunks.append(current)
                current = ""
    if current:
        chunks.append(current)
    return chunks or [text]


def tts_to_wav(model: object, text: str, speaker_id: int, output: Path, speed: float) -> None:
    chunks = speech_chunks(text)
    if len(chunks) == 1:
        model.tts_to_file(chunks[0], speaker_id, str(output), speed=speed)
        return
    parts: list[Path] = []
    try:
        for index, chunk in enumerate(chunks):
            part = output.parent / f".{output.stem}-{index}-{uuid.uuid4().hex}.wav"
            model.tts_to_file(chunk, speaker_id, str(part), speed=speed)
            parts.append(part)
        with wave.open(str(parts[0]), "rb") as first:
            parameters = first.getparams()
            frames = [first.readframes(first.getnframes())]
        for part in parts[1:]:
            with wave.open(str(part), "rb") as source:
                if source.getparams()[:3] != parameters[:3]:
                    raise RuntimeError("OpenVoice generated incompatible speech segments.")
                frames.append(source.readframes(source.getnframes()))
        with wave.open(str(output), "wb") as combined:
            combined.setparams(parameters)
            for frame in frames:
                combined.writeframes(frame)
    finally:
        for part in parts:
            part.unlink(missing_ok=True)


class VoiceRuntime:
    def __init__(self, root: Path) -> None:
        add_ffmpeg_to_path()
        sys.path.insert(0, str(root))
        import torch
        from melo.api import TTS
        from openvoice.api import ToneColorConverter

        self.torch = torch
        self.root = root
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model = TTS(language="EN_NEWEST", device=self.device)
        checkpoint_root = root / "checkpoints_v2"
        self.converter = ToneColorConverter(str(checkpoint_root / "converter" / "config.json"), device=self.device)
        self.converter.load_ckpt(str(checkpoint_root / "converter" / "checkpoint.pth"))
        self.checkpoint_root = checkpoint_root
        self.last_synthesis = time.monotonic()
        self.lock = threading.Lock()

    def synthesize(self, payload: dict[str, object]) -> dict[str, str]:
        with self.lock:
            return self._synthesize(payload)

    def _synthesize(self, payload: dict[str, object]) -> dict[str, str]:
        self.last_synthesis = time.monotonic()
        text = text_for_speech(str(payload.get("text", "")))
        if not text:
            raise ValueError("The reply did not contain speakable text.")
        output = Path(str(payload["output"])).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        speaker = str(payload.get("speaker", "EN-Newest"))
        speaker_ids = self.model.hps.data.spk2id
        speaker_id = speaker_ids[speaker] if speaker in speaker_ids else next(iter(speaker_ids.values()))
        reference_value = str(payload.get("reference", ""))
        if not reference_value:
            tts_to_wav(self.model, text, speaker_id, output, float(payload.get("speed", 1.0)))
            return {"output": str(output)}

        reference = Path(reference_value).resolve()
        if not reference.is_file():
            raise FileNotFoundError("The selected voice reference was not found.")
        from openvoice import se_extractor

        cache_value = str(payload.get("embedding_cache", ""))
        embedding_cache = Path(cache_value).resolve() if cache_value else None
        if embedding_cache and embedding_cache.is_file():
            target_embedding = self.torch.load(str(embedding_cache), map_location=self.device).to(self.device)
        else:
            target_dir = embedding_cache.parent / "processed" if embedding_cache else output.parent / "voice-cache"
            target_embedding, _ = se_extractor.get_se(str(reference), self.converter, target_dir=str(target_dir), vad=True)
            if embedding_cache:
                embedding_cache.parent.mkdir(parents=True, exist_ok=True)
                self.torch.save(target_embedding.detach().cpu(), str(embedding_cache))
        source_embedding = self.checkpoint_root / "base_speakers" / "ses" / f"{speaker.lower().replace('_', '-')}.pth"
        if not source_embedding.is_file():
            raise FileNotFoundError(f"OpenVoice speaker embedding is missing: {source_embedding.name}")
        temporary = output.parent / f".{uuid.uuid4().hex}.wav"
        try:
            tts_to_wav(self.model, text, speaker_id, temporary, float(payload.get("speed", 1.0)))
            self.converter.convert(
                audio_src_path=str(temporary),
                src_se=self.torch.load(str(source_embedding), map_location=self.device),
                tgt_se=target_embedding,
                output_path=str(output),
                message="@AliceOS",
            )
        finally:
            temporary.unlink(missing_ok=True)
        return {"output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Persistent local OpenVoice worker for Alice OS.")
    parser.add_argument("--openvoice-root", required=True)
    parser.add_argument("--port", type=int, default=7791)
    parser.add_argument("--idle-seconds", type=int, default=300)
    args = parser.parse_args()
    runtime = VoiceRuntime(Path(args.openvoice_root).resolve())

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/health":
                self.send_error(404)
                return
            self._json(200, {"ready": True})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/synthesize":
                self.send_error(404)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(size))
                self._json(200, runtime.synthesize(payload))
            except Exception as error:  # convert local worker errors to Alice API errors
                self._json(500, {"detail": str(error)})

        def log_message(self, *_: object) -> None:
            return

        def _json(self, status: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.timeout = 2
    while True:
        server.handle_request()
        if args.idle_seconds > 0 and time.monotonic() - runtime.last_synthesis >= args.idle_seconds:
            break


if __name__ == "__main__":
    main()
