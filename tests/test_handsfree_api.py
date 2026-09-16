from __future__ import annotations

import asyncio
import io
import threading
import wave
from collections import deque

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from alice_os import api, handsfree
from alice_os.handsfree import FRAME_BYTES, ConversationLease

ENDPOINT = "/api/voice/conversation"
VOICE = b"\x01\x00" * (FRAME_BYTES // 2)
SILENCE = bytes(FRAME_BYTES)


class FakeVad:
    def is_speech(self, frame, sample_rate):
        assert sample_rate == 16000
        return frame == VOICE


@pytest.fixture
def local_runtime(monkeypatch):
    monkeypatch.delenv("ALICE_NETWORK_MODE", raising=False)
    monkeypatch.setattr(api, "transcription_status", lambda: {"ready": True})
    monkeypatch.setattr(handsfree.webrtcvad, "Vad", lambda _: FakeVad())


def authorized_headers(app, origin="http://testserver"):
    return {"origin": origin, "X-Alice-Token": app.state.session_token}


def configure(socket):
    socket.send_json({"type": "configure", "wake_phrase": "hey jarvis"})
    assert socket.receive_json()["state"] == "idle"


def send_utterance(socket):
    socket.send_bytes(VOICE * 10)
    socket.send_bytes(VOICE * 10)
    for _ in range(5):
        socket.send_bytes(SILENCE * 10)


def receive_until(socket, predicate):
    events = []
    for _ in range(15):
        event = socket.receive_json()
        events.append(event)
        if predicate(event):
            return events
    pytest.fail(f"Expected voice event was not received: {events}")


def assert_available(client, headers):
    with client.websocket_connect(ENDPOINT, headers=headers) as socket:
        ready = socket.receive_json()
        assert ready["event"] == "ready"
        assert ready["local"] is True
        assert ready["sample_rate"] == 16000


@pytest.mark.parametrize("origin,token", [
    ("http://testserver", None),
    ("http://testserver", "wrong-token"),
    (None, "valid"),
    ("https://evil.example", "valid"),
    ("http://testserver:9999", "valid"),
    ("https://testserver", "valid"),
    ("http://testserver/path", "valid"),
    ("http://testserver?query=1", "valid"),
    ("http://testserver#fragment", "valid"),
])
def test_conversation_requires_authentication_and_exact_origin(local_runtime, tmp_path, origin, token):
    app = api.create_app(tmp_path)
    headers = {}
    if origin is not None:
        headers["origin"] = origin
    if token is not None:
        headers["X-Alice-Token"] = app.state.session_token if token == "valid" else token
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(ENDPOINT, headers=headers):
                pytest.fail("An unauthorized microphone stream was accepted")
        assert error.value.code == 1008
        assert_available(client, authorized_headers(app))


def test_secure_socket_accepts_matching_secure_origin_and_session_cookie(local_runtime, tmp_path):
    app = api.create_app(tmp_path)
    with TestClient(app) as client:
        headers = {
            "origin": "https://testserver",
            "cookie": f"alice_session={app.state.session_token}",
        }
        with client.websocket_connect(f"wss://testserver{ENDPOINT}", headers=headers) as socket:
            assert socket.receive_json()["event"] == "ready"


def test_network_mode_also_requires_network_access_cookie(local_runtime, monkeypatch, tmp_path):
    monkeypatch.setenv("ALICE_NETWORK_MODE", "1")
    app = api.create_app(tmp_path)
    headers = authorized_headers(app)
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(ENDPOINT, headers=headers):
                pytest.fail("Network authentication was bypassed")
        assert error.value.code == 1008
        access = (tmp_path / "network-session-token").read_text(encoding="ascii").strip()
        headers["cookie"] = f"alice_network_access={access}"
        assert_available(client, headers)


def test_unavailable_transcription_does_not_acquire_conversation_lease(local_runtime, monkeypatch, tmp_path):
    app = api.create_app(tmp_path)
    monkeypatch.setattr(api, "transcription_status", lambda: {"ready": False, "message": "Install local Whisper."})
    with TestClient(app) as client:
        with client.websocket_connect(ENDPOINT, headers=authorized_headers(app)) as socket:
            assert socket.receive_json() == {
                "event": "error", "code": "unavailable", "recoverable": False,
                "message": "Install local Whisper.",
            }
            with pytest.raises(WebSocketDisconnect) as error:
                socket.receive_json()
            assert error.value.code == 1013
        monkeypatch.setattr(api, "transcription_status", lambda: {"ready": True})
        assert_available(client, authorized_headers(app))


def test_only_one_conversation_stream_is_allowed_and_normal_close_releases_it(local_runtime, tmp_path):
    app = api.create_app(tmp_path)
    headers = authorized_headers(app)
    with TestClient(app) as client:
        with client.websocket_connect(ENDPOINT, headers=headers) as first:
            assert first.receive_json()["event"] == "ready"
            with client.websocket_connect(ENDPOINT, headers=headers) as second:
                assert second.receive_json()["code"] == "in_use"
                with pytest.raises(WebSocketDisconnect) as error:
                    second.receive_json()
                assert error.value.code == 1013
        assert_available(client, headers)


@pytest.mark.parametrize("packet,configured", [
    (SILENCE, False),
    (b"", True),
    (b"bad", True),
    (SILENCE * 11, True),
    ("not json", True),
    ("[]", True),
    ("{}", True),
    ("x" * 2049, True),
    ('{"type":"context","busy":"yes"}', True),
    ('{"type":"configure","followup_seconds":-1}', True),
])
def test_invalid_packets_close_stream_and_release_lease(local_runtime, tmp_path, packet, configured):
    app = api.create_app(tmp_path)
    headers = authorized_headers(app)
    with TestClient(app) as client:
        with client.websocket_connect(ENDPOINT, headers=headers) as socket:
            assert socket.receive_json()["event"] == "ready"
            if configured:
                configure(socket)
            if isinstance(packet, bytes):
                socket.send_bytes(packet)
            else:
                socket.send_text(packet)
            with pytest.raises(WebSocketDisconnect) as error:
                socket.receive_json()
            assert error.value.code == 1008
        assert_available(client, headers)


def test_idle_speech_stays_local_and_wake_transcript_never_starts_a_run(local_runtime, monkeypatch, tmp_path):
    transcripts = deque(["Private household speech", "Hey Jarvis, tell me the time."])
    recordings = []

    async def transcribe(*, filename, content, on_partial=None):
        assert filename == "handsfree.wav"
        recordings.append(content)
        return {"text": transcripts.popleft()}

    monkeypatch.setattr(api, "transcribe_openvoice_audio", transcribe)
    app = api.create_app(tmp_path)
    with TestClient(app) as client:
        with client.websocket_connect(ENDPOINT, headers=authorized_headers(app)) as socket:
            assert socket.receive_json()["event"] == "ready"
            configure(socket)
            send_utterance(socket)
            idle = receive_until(socket, lambda event: event.get("state") == "idle")
            assert all(event["event"] not in {"transcript", "wake"} for event in idle)
            assert "Private household speech" not in str(idle)
            send_utterance(socket)
            awake = receive_until(socket, lambda event: event.get("state") == "busy")
            recognized = [event for event in awake if event["event"] == "transcript"]
            assert [event["text"] for event in recognized] == ["tell me the time."]
            assert len([event for event in awake if event["event"] == "wake"]) == 1
            assert app.state.runs.runs == {}
            assert app.state.storage.list_sessions() == []
    assert len(recordings) == 2
    for audio in recordings:
        with wave.open(io.BytesIO(audio), "rb") as recording:
            assert (recording.getnchannels(), recording.getsampwidth(), recording.getframerate()) == (1, 2, 16000)


def test_disconnect_keeps_lease_until_pending_inference_finishes(local_runtime, monkeypatch, tmp_path):
    started = threading.Event()
    closed = threading.Event()
    released = threading.Event()
    finish = asyncio.Event()
    cancelled = []
    original_release = ConversationLease.release

    class ObservedConversation(handsfree.HandsFreeConversation):
        def close(self):
            pending = super().close()
            closed.set()
            return pending

    def release(cls, owner):
        original_release(owner)
        released.set()

    async def transcribe(**kwargs):
        started.set()
        try:
            await finish.wait()
        except asyncio.CancelledError:
            cancelled.append(True)
            raise
        return {"text": "Hey Jarvis, a late request"}

    monkeypatch.setattr(api, "HandsFreeConversation", ObservedConversation)
    monkeypatch.setattr(api, "transcribe_openvoice_audio", transcribe)
    monkeypatch.setattr(ConversationLease, "release", classmethod(release))
    app = api.create_app(tmp_path)
    headers = authorized_headers(app)
    with TestClient(app) as client:
        with client.websocket_connect(ENDPOINT, headers=headers) as first:
            assert first.receive_json()["event"] == "ready"
            configure(first)
            send_utterance(first)
            try:
                assert started.wait(5)
                first.close()
                assert closed.wait(5)
                with client.websocket_connect(ENDPOINT, headers=headers) as second:
                    assert second.receive_json()["code"] == "in_use"
                assert not released.is_set()
                assert not cancelled
            finally:
                first.portal.call(finish.set)
            assert released.wait(5)
            assert not cancelled
            assert app.state.runs.runs == {}
            assert app.state.storage.list_sessions() == []
            assert_available(client, headers)
