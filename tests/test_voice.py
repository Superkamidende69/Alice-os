from __future__ import annotations

import asyncio
import importlib.util
import threading
import wave
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from alice_os.api import create_app
from alice_os.vad import SpeechActivityDetector
from alice_os.voice import VoiceCancellation, VoiceInterrupted

spec = importlib.util.spec_from_file_location(
    "voice_speech", Path(__file__).resolve().parents[1] / "scripts" / "voice_speech.py"
)
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)


def test_vad_requires_sustained_speech_and_rearms_after_silence():
    detector = SpeechActivityDetector()
    voiced = True

    class Classifier:
        def is_speech(self, *_):
            return voiced

    detector.vad = Classifier()
    frame = bytes(detector.frame_bytes)
    assert detector.feed(frame * 3) == []  # a brief transient cannot interrupt
    voiced = False
    assert detector.feed(frame * 10) == []
    voiced = True
    assert detector.feed(frame * 8) == ["speech_start"]
    assert detector.feed(frame * 10) == []
    voiced = False
    assert detector.feed(frame * 10) == []
    assert detector.feed(frame * 10) == []
    assert detector.feed(frame * 5) == ["speech_end"]
    voiced = True
    assert detector.feed(frame * 8) == ["speech_start"]


def test_real_vad_silence_and_frame_validation():
    detector = SpeechActivityDetector()
    for _ in range(10):
        assert detector.feed(bytes(1920)) == []
    for invalid in (b"", b"a", bytes(642), bytes(7040)):
        with pytest.raises(ValueError):
            detector.feed(invalid)


def test_voice_socket_authentication_origin_and_format(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        for headers in (
            {"origin": "http://testserver"},
            {"origin": "https://evil.example", "X-Alice-Token": app.state.session_token},
            {"origin": "http://testserver:9999", "X-Alice-Token": app.state.session_token},
        ):
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/api/voice/activity", headers=headers):
                    pass
        headers = {"origin": "http://testserver", "X-Alice-Token": app.state.session_token}
        with client.websocket_connect("/api/voice/activity", headers=headers) as socket:
            assert socket.receive_json()["event"] == "ready"
            socket.send_bytes(bytes(1920))
            socket.send_bytes(b"bad")
            with pytest.raises(WebSocketDisconnect) as error:
                socket.receive_json()
            assert error.value.code == 1008


@pytest.mark.asyncio
async def test_cancel_during_synthesis_never_publishes_audio(monkeypatch, tmp_path):
    started = asyncio.Event()
    finish = asyncio.Event()

    async def synthesize(**kwargs):
        started.set()
        await finish.wait()
        assert kwargs["cancellation"].path.exists()
        return {"audio": b"late audio"}

    monkeypatch.setattr("alice_os.api.synthesize_openvoice", synthesize)
    app = create_app(tmp_path)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            headers = {"X-Alice-Token": app.state.session_token}
            request = asyncio.create_task(client.post("/api/voice/synthesize", headers=headers, json={"text": "Hello", "request_id": "turn-1"}))
            await started.wait()
            cancelled = await client.post("/api/voice/cancel", headers=headers, json={"request_id": "turn-1"})
            assert cancelled.status_code == 200
            finish.set()
            assert (await request).status_code == 409
            assert app.state.audio_cache == {}


def test_cancel_before_synthesis_is_authenticated_and_remembered(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        body = {"request_id": "early"}
        assert client.post("/api/voice/cancel", json=body).status_code == 401
        headers = {"X-Alice-Token": app.state.session_token}
        assert client.post("/api/voice/cancel", headers=headers, json=body).status_code == 200
        assert client.post("/api/voice/synthesize", headers=headers, json={**body, "text": "Hello"}).status_code == 409


def test_speech_cleanup_keeps_words_and_link_labels():
    assert speech.text_for_speech("Hello\nworld — [read this](https://example.com).") == "Hello world , read this."
    assert "secret_code" not in speech.text_for_speech("Here:\n```python\nsecret_code()\n```")
    assert speech.text_for_speech("Dr. Ada & Bob, e.g. the team") == "Doctor Ada and Bob, for example the team"
    text = "This is a complete thought. " * 30
    chunks = speech.speech_chunks(text)
    assert all(len(chunk) <= 240 for chunk in chunks)
    assert " ".join(chunks) == text.strip()


def test_speech_chunks_do_not_split_after_titles_or_initials():
    chunks = speech.speech_chunks("Dr. Ada works. B. Smith agrees.", limit=10)
    assert chunks[0] == "Dr. Ada"
    assert "B." not in chunks
    assert speech.pause_after("Question?") > speech.pause_after("Clause,")


def test_synthesis_checks_cancellation_between_segments_and_cleans_parts(tmp_path):
    cancellation = VoiceCancellation()
    calls = []

    class Model:
        def tts_to_file(self, text, speaker, output, **kwargs):
            calls.append(text)
            Path(output).write_bytes(b"partial")
            cancellation.cancel()

    try:
        with pytest.raises(VoiceInterrupted):
            speech.tts_to_wav(Model(), "Long sentence. " * 50, 0, tmp_path / "out.wav", 1, .6, .8, .2, cancellation.check)
        assert len(calls) == 1
        assert list(tmp_path.iterdir()) == []
    finally:
        cancellation.close()


def test_failed_segment_is_cleaned_up(tmp_path):
    class Model:
        def tts_to_file(self, text, speaker, output, **kwargs):
            Path(output).write_bytes(b"partial")
            raise RuntimeError("inference failed")

    with pytest.raises(RuntimeError):
        speech.tts_to_wav(Model(), "Hello.", 0, tmp_path / "out.wav", 1, .6, .8, .2)
    assert list(tmp_path.iterdir()) == []


def test_audio_segments_have_consistent_format_and_brief_pauses(tmp_path):
    class Model:
        def tts_to_file(self, text, speaker, output, **kwargs):
            with wave.open(output, "wb") as clip:
                clip.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                clip.writeframes(bytes(3200))

    text = "This is a sentence. " * 30
    output = tmp_path / "out.wav"
    speech.tts_to_wav(Model(), text, 0, output, 1, .6, .8, .2)
    count = len(speech.speech_chunks(text))
    with wave.open(str(output)) as clip:
        assert clip.getframerate() == 16000
    assert clip.getnframes() == count * (1600 + int(16000 * 0.32))
    assert list(tmp_path.iterdir()) == [output]


def test_short_speech_splits_commas_sentences_and_quotes_without_splitting_numbers():
    assert speech.speech_chunks('First, take a breath. Then say "hello." Next!') == [
        "First,", "take a breath.", 'Then say "hello."', "Next!",
    ]
    assert speech.speech_chunks("It costs 1,000.50 dollars,not 3.14. Dr. Ada agrees.") == [
        "It costs 1,000.50 dollars,", "not 3.14.", "Dr. Ada agrees.",
    ]
    assert speech.pause_after('Done."') == speech.pause_after("Done.") == .32
    assert speech.pause_after("Dr.") < speech.pause_after("Done.")


def test_punctuation_pauses_are_written_to_short_streamed_wav(tmp_path):
    calls = []

    class Model:
        def tts_to_file(self, text, speaker, output, **kwargs):
            calls.append(text)
            with wave.open(output, "wb") as clip:
                clip.setparams((1, 2, 1000, 0, "NONE", "not compressed"))
                clip.writeframes(b"\x01\x01" * 100)

    output = tmp_path / "punctuation.wav"
    speech.tts_to_wav(Model(), "Hello, world. Next sentence.", 0, output, 1.15, .6, .8, .2)
    assert calls == ["Hello,", "world.", "Next sentence."]
    with wave.open(str(output), "rb") as clip:
        actual = clip.readframes(clip.getnframes())
    tone = b"\x01\x01" * 100
    assert actual == tone + bytes(320) + tone + bytes(640) + tone + bytes(640)
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.asyncio
async def test_worker_interruption_does_not_trigger_fallback(monkeypatch, tmp_path):
    import alice_os.voice as voice

    started = threading.Event()
    release = threading.Event()

    async def ensure(_):
        pass

    def request(*args):
        started.set()
        release.wait(5)
        raise voice.VoiceError("Speech was interrupted.")

    async def forbidden(*args, **kwargs):
        pytest.fail("An interrupted worker must never run the one-shot fallback")

    monkeypatch.setattr(voice, "openvoice_status", lambda: {"ready": True, "root": str(tmp_path)})
    monkeypatch.setattr(voice, "_ensure_openvoice_worker", ensure)
    monkeypatch.setattr(voice, "_worker_request", request)
    monkeypatch.setattr(voice, "_run_voice_process", forbidden)
    monkeypatch.setattr(voice, "_openvoice_request_lock", asyncio.Lock())
    cancellation = VoiceCancellation()
    try:
        task = asyncio.create_task(voice.synthesize_openvoice(data_dir=tmp_path, text="Hello", speaker="EN-Newest", cancellation=cancellation))
        assert await asyncio.to_thread(started.wait, 5)
        cancellation.cancel()
        release.set()
        with pytest.raises(VoiceInterrupted):
            await task
    finally:
        release.set()
        cancellation.close()
