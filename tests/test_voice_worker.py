from __future__ import annotations

import builtins
import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def worker(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("alice_test_voice_worker", scripts / "openvoice_worker.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "add_ffmpeg_to_path", lambda: None)
    return module


def mock_whisper(monkeypatch, segments=None):
    calls = []

    class Whisper:
        def __init__(self, model, **kwargs):
            calls.append({"model": model, **kwargs})

        def transcribe(self, path, **kwargs):
            return (segments() if segments else [SimpleNamespace(text=" Hello Alice ")],
                    SimpleNamespace(language="en"))

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Whisper))
    return calls


def mock_speech(monkeypatch, runtime, *, fail_once=False):
    calls = []

    def tts(**kwargs):
        assert runtime.lock.locked()
        calls.append("tts")
        return SimpleNamespace(hps=SimpleNamespace(data=SimpleNamespace(spk2id={"EN-Newest": 0})))

    class Converter:
        def __init__(self, *args, **kwargs):
            pass

        def load_ckpt(self, path):
            calls.append("converter")
            if fail_once and calls.count("converter") == 1:
                raise RuntimeError("Mock checkpoint failed")

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False), inference_mode=nullcontext))
    monkeypatch.setitem(sys.modules, "melo.api", SimpleNamespace(TTS=tts))
    monkeypatch.setitem(sys.modules, "openvoice.api", SimpleNamespace(ToneColorConverter=Converter))
    return calls


def test_cpu_transcription_starts_without_importing_speech_dependencies(worker, monkeypatch, tmp_path):
    calls = mock_whisper(monkeypatch)
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".", 1)[0] in {"torch", "melo", "openvoice"}:
            raise AssertionError(f"Dictation must not import {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    runtime = worker.VoiceRuntime(tmp_path)
    recording = tmp_path / "recording.wav"
    recording.write_bytes(b"mock audio")
    result = runtime.transcribe({"input": str(recording), "model_dir": str(tmp_path / "whisper")})
    assert result == {"text": "Hello Alice", "language": "en"}
    assert runtime.model is None and runtime.converter is None
    assert calls == [{"model": "base", "device": "cpu", "compute_type": "int8", "download_root": str(tmp_path / "whisper")}]


def test_failed_speech_warm_is_retryable_and_successful_load_is_reused(worker, monkeypatch, tmp_path):
    runtime = worker.VoiceRuntime(tmp_path)
    calls = mock_speech(monkeypatch, runtime, fail_once=True)
    with pytest.raises(RuntimeError, match="checkpoint"):
        runtime.warm()
    assert runtime.model is None and runtime.active_requests == 0
    assert runtime.warm() == {"ready": True}
    assert runtime.warm() == {"ready": True}
    assert calls == ["tts", "converter", "tts", "converter"]


def test_synthesis_loads_speech_lazily_under_lock(worker, monkeypatch, tmp_path):
    runtime = worker.VoiceRuntime(tmp_path)
    calls = mock_speech(monkeypatch, runtime)
    monkeypatch.setattr(worker, "tts_to_wav", lambda model, text, speaker, output, *args: output.write_bytes(b"RIFFmock"))
    output = tmp_path / "speech.wav"
    assert calls == []
    assert runtime.synthesize({"text": "Hello", "output": str(output)}) == {"output": str(output.resolve())}
    assert output.read_bytes() == b"RIFFmock"
    assert calls == ["tts", "converter"]
    assert runtime.active_requests == 0


def test_dictation_keeps_worker_alive_and_can_run_while_speech_lock_is_held(worker, monkeypatch, tmp_path):
    now = [10.0]
    monkeypatch.setattr(worker.time, "monotonic", lambda: now[0])
    runtime = worker.VoiceRuntime(tmp_path)

    def segments():
        now[0] = 1000.0
        assert runtime.active_requests == 1
        assert not runtime.idle_expired(5)
        yield SimpleNamespace(text="Still listening")

    mock_whisper(monkeypatch, segments)
    recording = tmp_path / "recording.wav"
    recording.write_bytes(b"mock audio")
    with ThreadPoolExecutor(max_workers=1) as executor:
        runtime.lock.acquire()
        try:
            future = executor.submit(runtime.transcribe, {"input": str(recording)})
            assert future.result(timeout=2)["text"] == "Still listening"
        finally:
            runtime.lock.release()
    assert runtime.last_activity == 1000.0
    assert runtime.active_requests == 0
    assert not runtime.idle_expired(5)
    now[0] = 1006.0
    assert runtime.idle_expired(5)
    assert not runtime.idle_expired(0)


def test_cancelled_synthesis_does_not_load_weights(worker, monkeypatch, tmp_path):
    runtime = worker.VoiceRuntime(tmp_path)
    calls = mock_speech(monkeypatch, runtime)
    cancellation = tmp_path / "cancelled"
    cancellation.touch()
    with pytest.raises(RuntimeError, match="interrupted"):
        runtime.synthesize({"text": "Hello", "cancel_path": str(cancellation)})
    assert calls == []
    assert runtime.active_requests == 0
