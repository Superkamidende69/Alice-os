import asyncio
import threading
from pathlib import Path

import pytest

from alice_os import kokoro
from alice_os.voice import VoiceCancellation, VoiceError, VoiceInterrupted, synthesize_openvoice


@pytest.mark.asyncio
async def test_kokoro_routing_preserves_speed_and_rejects_cloning(monkeypatch, tmp_path):
    calls = []
    async def synthesize(*args):
        calls.append(args)
        return {"audio": b"RIFFtest"}
    monkeypatch.setattr(kokoro, "synthesize", synthesize)
    result = await synthesize_openvoice(data_dir=tmp_path, text="Hello, Alice.", speaker="KOKORO-HEART", speed=.9)
    assert result["audio"] == b"RIFFtest"
    assert calls[0][:3] == ("Hello, Alice.", "KOKORO-HEART", .9)
    with pytest.raises(VoiceError, match="reference"):
        await synthesize_openvoice(data_dir=tmp_path, text="Hello", speaker="KOKORO-HEART", reference="sample.wav")


@pytest.mark.asyncio
async def test_cancellation_waits_for_worker_before_removing_output(monkeypatch, tmp_path):
    started, ended = threading.Event(), threading.Event()
    paths = []
    def request(payload, data_dir, stopped):
        path = Path(payload["output"])
        paths.append(path)
        started.set()
        assert stopped.wait(5)
        assert path.parent.exists()
        ended.set()
    monkeypatch.setattr(kokoro, "status", lambda: {"ready": True})
    monkeypatch.setattr(kokoro, "_request", request)
    marker = VoiceCancellation()
    try:
        task = asyncio.create_task(kokoro.synthesize("Hello", "KOKORO-HEART", 1, tmp_path, marker))
        assert await asyncio.to_thread(started.wait, 3)
        marker.cancel()
        with pytest.raises(VoiceInterrupted):
            await task
        assert ended.is_set()
        assert not paths[0].parent.exists()
    finally:
        marker.close()


@pytest.mark.asyncio
async def test_kokoro_missing_install_and_unknown_voice_are_explicit(monkeypatch, tmp_path):
    monkeypatch.setenv("ALICE_KOKORO_HOME", str(tmp_path))
    with pytest.raises(VoiceError, match="not installed"):
        await synthesize_openvoice(data_dir=tmp_path, text="Hello", speaker="KOKORO-HEART")
    with pytest.raises(VoiceError, match="Unknown"):
        await synthesize_openvoice(data_dir=tmp_path, text="Hello", speaker="KOKORO-NOPE")
