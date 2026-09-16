from __future__ import annotations

import asyncio
import io
import json
import threading
from pathlib import Path

import pytest

from alice_os import voice


@pytest.fixture
def transcription_runtime(monkeypatch, tmp_path):
    async def ensure(_):
        pass

    monkeypatch.setattr(voice, "transcription_status", lambda: {"ready": True})
    monkeypatch.setattr(voice, "_openvoice_root", lambda: tmp_path)
    monkeypatch.setattr(voice, "_ensure_openvoice_worker", ensure)
    monkeypatch.setattr(voice, "_openvoice_request_lock", asyncio.Lock())
    monkeypatch.setattr(voice, "_openvoice_transcription_lock", asyncio.Lock())


@pytest.mark.asyncio
@pytest.mark.parametrize("worker_fails", [False, True])
async def test_cancelled_transcription_keeps_input_and_slot_until_worker_finishes(
    transcription_runtime, monkeypatch, worker_fails,
):
    started = threading.Event()
    release = threading.Event()
    inputs = []

    def request(path, payload, timeout):
        assert path == "/transcribe"
        input_path = Path(payload["input"])
        inputs.append(input_path)
        assert input_path.read_bytes() == b"recorded audio"
        if len(inputs) == 1:
            started.set()
            assert release.wait(5), "The test did not release its worker"
            assert input_path.is_file(), "Cancellation removed an in-use recording"
            if worker_fails:
                raise voice.VoiceError("The worker stopped")
        return {"text": "A local reply", "language": "en"}

    monkeypatch.setattr(voice, "_worker_request", request)
    first = asyncio.create_task(
        voice.transcribe_openvoice_audio(filename="first.wav", content=b"recorded audio")
    )
    second = None
    try:
        assert await asyncio.to_thread(started.wait, 5)
        first.cancel()
        await asyncio.sleep(0)
        second = asyncio.create_task(
            voice.transcribe_openvoice_audio(filename="second.wav", content=b"recorded audio")
        )
        await asyncio.sleep(0)
        first.cancel()  # Repeated disconnect/stop must preserve the same lifetime.
        await asyncio.sleep(0)
        assert not first.done()
        assert not second.done()
        assert len(inputs) == 1
        assert inputs[0].is_file()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(first, 5)
        assert await asyncio.wait_for(second, 5) == {"text": "A local reply", "language": "en"}
        assert len(inputs) == 2
        assert not any(path.exists() for path in inputs)
    finally:
        release.set()
        if second is not None:
            second.cancel()
        await asyncio.gather(first, *([second] if second is not None else []), return_exceptions=True)


@pytest.mark.asyncio
async def test_transcription_can_finish_while_tts_request_lock_is_held(
    transcription_runtime, monkeypatch,
):
    inputs = []

    def request(path, payload, timeout):
        input_path = Path(payload["input"])
        assert input_path.is_file()
        inputs.append(input_path)
        return {"text": "An interruption", "language": "en"}

    monkeypatch.setattr(voice, "_worker_request", request)
    async with voice._openvoice_lock():
        result = await asyncio.wait_for(
            voice.transcribe_openvoice_audio(filename="speech.wav", content=b"recorded audio"),
            5,
        )
    assert result == {"text": "An interruption", "language": "en"}
    assert len(inputs) == 1
    assert not inputs[0].exists()


@pytest.mark.parametrize("events", [
    [{"text": "unfinished", "final": False}],
    [{"text": "done", "final": True}, {"text": "late", "final": False}],
    [["invalid"]],
])
def test_stream_rejects_incomplete_or_invalid_results(monkeypatch, events):
    data = b"".join((json.dumps(event) + "\n").encode() for event in events)
    monkeypatch.setattr(voice, "urlopen", lambda *args, **kwargs: io.BytesIO(data))
    with pytest.raises(voice.VoiceError):
        voice._worker_stream_request("/transcribe", {}, lambda event: None)


async def test_partial_callback_failure_holds_input_until_worker_finishes(transcription_runtime, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    inputs = []

    def request(path, payload, emit, timeout):
        inputs.append(Path(payload["input"]))
        emit({"text": "partial", "final": False})
        started.set()
        assert release.wait(5)
        assert inputs[0].is_file()
        emit({"text": "done", "final": True})

    async def partial(event):
        raise RuntimeError("Browser disconnected")

    monkeypatch.setattr(voice, "_worker_stream_request", request)
    task = asyncio.create_task(voice.transcribe_openvoice_audio(
        filename="speech.wav", content=b"recorded audio", on_partial=partial))
    try:
        assert await asyncio.to_thread(started.wait, 5)
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(RuntimeError, match="Browser disconnected"):
            await task
        assert not inputs[0].exists()
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_warmup_posts_and_allows_cold_model_loading(monkeypatch, tmp_path):
    async def ensure(root):
        pass

    calls = []
    monkeypatch.setattr(voice, "openvoice_status", lambda: {"ready": True, "root": str(tmp_path)})
    monkeypatch.setattr(voice, "_ensure_openvoice_worker", ensure)
    monkeypatch.setattr(voice, "_worker_request", lambda *args: calls.append(args))
    assert (await voice.warm_openvoice())["warmed"]
    assert calls == [("/warm", {}, 300)]
