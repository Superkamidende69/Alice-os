from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from voice_speech import text_for_speech, tts_to_wav


def add_ffmpeg_to_path() -> None:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return
    packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    for executable in packages.glob("Gyan.FFmpeg.Essentials*/**/bin/ffmpeg.exe"):
        os.environ["PATH"] = str(executable.parent) + os.pathsep + os.environ.get("PATH", "")
        return


class VoiceRuntime:
    def __init__(self, root: Path) -> None:
        add_ffmpeg_to_path()
        sys.path.insert(0, str(root))
        self.root = root
        self.checkpoint_root = root / "checkpoints_v2"
        self.torch = None
        self.model = None
        self.converter = None
        self.device = "cpu"
        self.last_activity = time.monotonic()
        self.active_requests = 0
        self.activity_lock = threading.Lock()
        self.lock = threading.Lock()
        self.transcription_lock = threading.Lock()
        self.source_embeddings: dict[str, object] = {}
        self.target_embeddings: dict[Path, object] = {}
        self.whisper_model: object | None = None
        self.whisper_model_dir = ""

    def health(self) -> dict[str, object]:
        with self.activity_lock:
            active_requests = self.active_requests
        return {
            "ready": True,
            "speech_loaded": self.model is not None,
            "transcription_loaded": self.whisper_model is not None,
            "active_requests": active_requests,
            "device": self.device,
        }

    @contextmanager
    def activity(self):
        # Count requests before they wait for a model lock, so queued work cannot
        # be mistaken for an idle worker. Dictation has its own CPU model lock.
        with self.activity_lock:
            self.active_requests += 1
            self.last_activity = time.monotonic()
        try:
            yield
        finally:
            with self.activity_lock:
                self.active_requests -= 1
                self.last_activity = time.monotonic()

    def idle_expired(self, seconds: float) -> bool:
        with self.activity_lock:
            return (seconds > 0 and self.active_requests == 0
                    and time.monotonic() - self.last_activity >= seconds)

    def _load_speech(self) -> None:
        """Load GPU speech weights on demand while the speech lock is held."""
        if self.model is not None:
            return
        import torch
        from melo.api import TTS
        from openvoice.api import ToneColorConverter

        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        if device.startswith("cuda"):
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
        model = TTS(language="EN_NEWEST", device=device)
        converter = ToneColorConverter(str(self.checkpoint_root / "converter" / "config.json"), device=device)
        converter.load_ckpt(str(self.checkpoint_root / "converter" / "checkpoint.pth"))
        # Publish only a complete load; a failed load remains retryable and does
        # not affect the independent Whisper transcription runtime.
        self.torch = torch
        self.device = device
        self.converter = converter
        self.model = model

    def warm(self) -> dict[str, bool]:
        with self.activity(), self.lock:
            self._load_speech()
            return {"ready": True}

    def source_embedding(self, speaker: str) -> object:
        key = speaker.lower().replace("_", "-")
        if key not in self.source_embeddings:
            path = self.checkpoint_root / "base_speakers" / "ses" / f"{key}.pth"
            if not path.is_file():
                raise FileNotFoundError(f"OpenVoice speaker embedding is missing: {path.name}")
            self.source_embeddings[key] = self.torch.load(str(path), map_location=self.device)
        return self.source_embeddings[key]

    def synthesize(self, payload: dict[str, object]) -> dict[str, str]:
        with self.activity(), self.lock:
            return self._synthesize(payload)

    def _synthesize(self, payload: dict[str, object]) -> dict[str, str]:
        cancel_path = str(payload.get("cancel_path", ""))

        def check_cancel() -> None:
            if cancel_path and Path(cancel_path).exists():
                raise RuntimeError("Speech was interrupted.")

        check_cancel()
        text = text_for_speech(str(payload.get("text", "")))
        if not text:
            raise ValueError("The reply did not contain speakable text.")
        self._load_speech()
        check_cancel()
        output = Path(str(payload["output"])).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        speaker = str(payload.get("speaker", "EN-Newest"))
        speaker_ids = self.model.hps.data.spk2id
        speaker_id = speaker_ids[speaker] if speaker in speaker_ids else next(iter(speaker_ids.values()))
        noise_scale = max(0.2, min(float(payload.get("noise_scale", 0.6)), 1.2))
        noise_scale_w = max(0.2, min(float(payload.get("noise_scale_w", 0.8)), 1.4))
        sdp_ratio = max(0.0, min(float(payload.get("sdp_ratio", 0.2)), 1.0))
        reference_value = str(payload.get("reference", ""))
        with self.torch.inference_mode():
            if not reference_value:
                tts_to_wav(
                    self.model, text, speaker_id, output, float(payload.get("speed", 1.0)),
                    noise_scale, noise_scale_w, sdp_ratio, check_cancel,
                )
                return {"output": str(output)}

            reference = Path(reference_value).resolve()
            if not reference.is_file():
                raise FileNotFoundError("The selected voice reference was not found.")
            from openvoice import se_extractor

            cache_value = str(payload.get("embedding_cache", ""))
            embedding_cache = Path(cache_value).resolve() if cache_value else None
            if embedding_cache in self.target_embeddings:
                target_embedding = self.target_embeddings[embedding_cache]
            elif embedding_cache and embedding_cache.is_file():
                target_embedding = self.torch.load(str(embedding_cache), map_location=self.device).to(self.device)
                self.target_embeddings[embedding_cache] = target_embedding
            else:
                target_dir = embedding_cache.parent / "processed" if embedding_cache else output.parent / "voice-cache"
                target_embedding, _ = se_extractor.get_se(str(reference), self.converter, target_dir=str(target_dir), vad=True)
                if embedding_cache:
                    embedding_cache.parent.mkdir(parents=True, exist_ok=True)
                    self.torch.save(target_embedding.detach().cpu(), str(embedding_cache))
                    self.target_embeddings[embedding_cache] = target_embedding
            temporary = output.parent / f".{uuid.uuid4().hex}.wav"
            try:
                tts_to_wav(
                    self.model, text, speaker_id, temporary, float(payload.get("speed", 1.0)),
                    noise_scale, noise_scale_w, sdp_ratio, check_cancel,
                )
                check_cancel()
                self.converter.convert(
                    audio_src_path=str(temporary),
                    src_se=self.source_embedding(speaker),
                    tgt_se=target_embedding,
                    output_path=str(output),
                    message="@AliceOS",
                )
                check_cancel()
            finally:
                temporary.unlink(missing_ok=True)
        return {"output": str(output)}

    def transcribe(self, payload: dict[str, object]) -> dict[str, str]:
        final = {"text": "", "language": ""}
        for event in self.transcribe_stream(payload):
            final = {"text": event["text"], "language": event["language"]}
        return final

    def transcribe_stream(self, payload: dict[str, object]):
        with self.activity(), self.transcription_lock:
            input_path = Path(str(payload["input"])).resolve()
            if not input_path.is_file():
                raise FileNotFoundError("The dictation recording was not found.")
            model_dir = str(payload.get("model_dir", ""))
            if self.whisper_model is None or self.whisper_model_dir != model_dir:
                from faster_whisper import WhisperModel

                # INT8 CPU inference is dependable on every supported Alice PC;
                # it does not require a matching CUDA/cuDNN installation.
                model_name = str(os.environ.get("ALICE_WHISPER_MODEL", "base")).strip().casefold()
                if model_name not in {"tiny", "base", "small", "medium"}:
                    model_name = "base"
                self.whisper_model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=model_dir)
                self.whisper_model_dir = model_dir
            try:
                beam_size = max(1, min(int(os.environ.get("ALICE_WHISPER_BEAM_SIZE", "1")), 5))
            except ValueError:
                beam_size = 1
            segments, info = self.whisper_model.transcribe(
                str(input_path), beam_size=beam_size, vad_filter=True, condition_on_previous_text=False,
            )
            language = str(getattr(info, "language", ""))
            words = []
            for segment in segments:
                value = segment.text.strip()
                if value:
                    words.append(value)
                    yield {"text": " ".join(words), "language": language, "final": False}
            yield {"text": " ".join(words), "language": language, "final": True}


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
            self._json(200, runtime.health())

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/warm":
                try:
                    self._json(200, runtime.warm())
                except Exception as error:
                    self._json(500, {"detail": str(error)})
                return
            if self.path == "/transcribe":
                streaming = False
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    payload = json.loads(self.rfile.read(size))
                    if payload.get("stream"):
                        streaming = True
                        self.send_response(200)
                        self.send_header("Content-Type", "application/x-ndjson")
                        self.send_header("Transfer-Encoding", "chunked")
                        self.end_headers()
                        for event in runtime.transcribe_stream(payload):
                            body = (json.dumps(event) + "\n").encode()
                            self.wfile.write(f"{len(body):X}\r\n".encode() + body + b"\r\n")
                            self.wfile.flush()
                        self.wfile.write(b"0\r\n\r\n")
                        self.wfile.flush()
                    else:
                        self._json(200, runtime.transcribe(payload))
                except Exception as error:
                    if streaming:
                        # A failed body must not contain a second HTTP response.
                        # Closing without the terminating chunk signals truncation.
                        self.close_connection = True
                    else:
                        try:
                            self._json(500, {"detail": str(error)})
                        except OSError:
                            pass
                return
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
    try:
        while True:
            server.handle_request()
            if runtime.idle_expired(args.idle_seconds):
                break
    finally:
        # ThreadingHTTPServer waits for accepted request threads here, including
        # one that may have started just as the idle check ran.
        server.server_close()


if __name__ == "__main__":
    main()
