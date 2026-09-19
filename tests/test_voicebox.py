import asyncio
import io
import json
import wave

import httpx
import pytest
from fastapi.testclient import TestClient

from alice_os import voicebox
from alice_os.api import create_app
from alice_os.voice import VoiceCancellation, VoiceError, VoiceInterrupted, synthesize_openvoice

PROFILE = "11bbce37-a05d-428d-8a66-a2ba398cd094"
JOB = "be5d9605-f9f6-4f89-a0ad-858898d94e04"


def wav():
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\0\0" * 240)
    return output.getvalue()


def mock_service(monkeypatch, *, states=None, fail_audio=False, cancellation=None):
    calls = []
    stages = iter(states or ["loading_model", "completed"])

    def handler(request):
        calls.append(request)
        path = request.url.path
        if path == "/":
            return httpx.Response(200, json={"message": "voicebox API", "version": "0.5.0"})
        profile = {"id": PROFILE, "name": "Test voice", "default_engine": "kokoro", "language": "en"}
        if path == "/profiles":
            return httpx.Response(200, json=[profile])
        if path == f"/profiles/{PROFILE}":
            return httpx.Response(200, json=profile)
        if path == "/generate":
            return httpx.Response(200, json={"id": JOB, "status": "generating", "audio_path": "http://evil.invalid/private"})
        if path == f"/history/{JOB}":
            if cancellation:
                cancellation.cancel()
            return httpx.Response(200, json={"id": JOB, "status": next(stages), "error": "Model unavailable"})
        if path == f"/audio/{JOB}":
            return httpx.Response(200, content=b"not audio" if fail_audio else wav())
        if path == f"/generate/{JOB}/cancel":
            return httpx.Response(200, json={"message": "Cancelled"})
        raise AssertionError(f"Unexpected request: {request.method} {path}")

    monkeypatch.setattr(voicebox, "client", lambda timeout=5: httpx.AsyncClient(
        base_url="http://127.0.0.1:17493", transport=httpx.MockTransport(handler)))
    return calls


@pytest.mark.parametrize("value", ["https://127.0.0.1:17493", "http://example.com", "http://127.0.0.1/private", "http://user:pass@localhost", "http://localhost?token=x", "http://localhost#fragment"])
def test_service_url_is_local_and_not_a_proxy(monkeypatch, value):
    monkeypatch.setenv("ALICE_VOICEBOX_URL", value)
    with pytest.raises(ValueError):
        voicebox.base_url()


def test_localhost_normalized_without_dns(monkeypatch):
    monkeypatch.setenv("ALICE_VOICEBOX_URL", "http://localhost:17493/")
    assert voicebox.base_url() == "http://127.0.0.1:17493"


@pytest.mark.asyncio
async def test_profile_discovery_and_alice_speech_pipeline(monkeypatch, tmp_path):
    calls = mock_service(monkeypatch)
    state = await voicebox.status()
    assert state["ready"]
    assert state["profiles"][0]["id"] == PROFILE
    result = await synthesize_openvoice(data_dir=tmp_path, text="Hello, Alice.", speaker="VOICEBOX:" + PROFILE)
    assert result["audio"] == wav()
    payload = json.loads(next(request.content for request in calls if request.url.path == "/generate"))
    assert payload["engine"] == "kokoro"
    assert payload["personality"] is False
    assert payload["text"] == "Hello, Alice."
    assert all(request.url.host == "127.0.0.1" for request in calls)
    assert not any(request.url.path.endswith("/cancel") for request in calls)


@pytest.mark.asyncio
async def test_interruption_cancels_only_the_created_job(monkeypatch):
    cancellation = VoiceCancellation()
    try:
        calls = mock_service(monkeypatch, cancellation=cancellation)
        with pytest.raises(VoiceInterrupted):
            await voicebox.synthesize("Hello", "VOICEBOX:" + PROFILE, cancellation)
        assert [r.url.path for r in calls if r.url.path.endswith("/cancel")] == [f"/generate/{JOB}/cancel"]
        assert not any(r.url.path.startswith("/audio/") for r in calls)
    finally:
        cancellation.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["failed", "unknown", "bad_audio"])
async def test_generation_failure_and_invalid_audio_surface_errors(monkeypatch, failure):
    calls = mock_service(monkeypatch, states=["completed" if failure == "bad_audio" else failure], fail_audio=failure == "bad_audio")
    with pytest.raises(VoiceError):
        await voicebox.synthesize("Hello", "VOICEBOX:" + PROFILE)
    assert calls[-1].url.path == f"/generate/{JOB}/cancel"


@pytest.mark.asyncio
async def test_no_generation_on_invalid_profile_or_openvoice_reference(monkeypatch, tmp_path):
    calls = mock_service(monkeypatch)
    with pytest.raises(VoiceError):
        await voicebox.synthesize("Hello", "VOICEBOX:../../shutdown")
    with pytest.raises(VoiceError, match="references"):
        await synthesize_openvoice(data_dir=tmp_path, text="Hello", speaker="VOICEBOX:" + PROFILE, reference="private.wav")
    assert not calls


def test_api_auth_and_remote_launch_restriction(monkeypatch, tmp_path):
    async def state():
        return {"ready": True, "profiles": []}
    monkeypatch.setattr(voicebox, "status", state)
    app = create_app(tmp_path / "data")
    with TestClient(app) as client:
        assert client.get("/api/voicebox/status").status_code == 401
        assert client.post("/api/voicebox/start").status_code == 401
        client.get("/")
        assert client.get("/api/voicebox/status").json()["ready"]
        monkeypatch.setattr("alice_os.api.is_host_client", lambda _: False)
        assert client.post("/api/voicebox/start").status_code == 403
        assert client.post("/api/voicebox/studio").status_code == 403


def test_alice_speech_api_accepts_profile_uuid_and_serves_audio(monkeypatch, tmp_path):
    async def synthesize(text, speaker, cancellation=None):
        assert speaker == "VOICEBOX:" + PROFILE
        return {"audio": wav()}
    monkeypatch.setattr(voicebox, "synthesize", synthesize)
    with TestClient(create_app(tmp_path / "data")) as client:
        client.get("/")
        response = client.post("/api/voice/synthesize", json={"text": "Hello", "speaker": "VOICEBOX:" + PROFILE})
        assert response.status_code == 200
        audio = client.get(response.json()["url"])
        assert audio.content == wav()
        assert audio.headers["content-type"] == "audio/wav"


@pytest.mark.asyncio
async def test_does_not_take_ownership_of_external_voicebox(monkeypatch, tmp_path):
    async def state():
        return {"ready": True}
    monkeypatch.setattr(voicebox, "status", state)
    monkeypatch.setattr(voicebox.subprocess, "Popen", lambda *a, **k: pytest.fail("External server must not be launched or stopped"))
    runtime = voicebox.Runtime(tmp_path)
    assert (await runtime.start())["ready"]
    assert runtime.process is None
    await runtime.stop()


@pytest.mark.asyncio
async def test_task_cancellation_requests_upstream_cancel(monkeypatch):
    calls = mock_service(monkeypatch, states=["generating"] * 100)
    task = asyncio.create_task(voicebox.synthesize("Hello", "VOICEBOX:" + PROFILE))
    while not any(r.url.path == "/generate" for r in calls):
        await asyncio.sleep(.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls[-1].url.path == f"/generate/{JOB}/cancel"
