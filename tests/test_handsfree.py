from __future__ import annotations

import asyncio
import io
import wave
from collections import deque

import pytest

from alice_os.handsfree import (
    FRAME_BYTES,
    MAX_UTTERANCE_MS,
    ConversationConfig,
    ConversationLease,
    HandsFreeConversation,
    SpeechSegmenter,
    extract_wake_command,
)

VOICE = b"\x01\x00" * (FRAME_BYTES // 2)
SILENCE = bytes(FRAME_BYTES)


class FakeVad:
    def is_speech(self, frame, sample_rate):
        assert len(frame) == FRAME_BYTES
        assert sample_rate == 16000
        return frame == VOICE


class Harness:
    def __init__(self, *texts):
        self.texts = deque(texts)
        self.events = []
        self.audio = []
        self.now = 100.0
        self.gate = None
        self.session = HandsFreeConversation(
            transcribe=self.transcribe, emit=self.emit,
            clock=lambda: self.now, vad=FakeVad(),
        )

    async def transcribe(self, *, filename, content, on_partial=None):
        assert filename == "handsfree.wav"
        self.audio.append(content)
        if self.gate:
            await self.gate.wait()
        return {"text": self.texts.popleft()}

    async def emit(self, event):
        self.events.append(event)

    async def configure(self, **settings):
        await self.session.control({"type": "configure", **settings})

    async def utterance(self, *, finish=True):
        for frame in [SILENCE] * 10 + [VOICE] * 20 + [SILENCE] * 43:
            await self.session.feed(frame)
        if finish and self.session.pending:
            await self.session.pending

    def named(self, name):
        return [event for event in self.events if event["event"] == name]


async def test_live_preview_before_silence_cannot_activate_or_submit_and_final_can_correct():
    harness = Harness("Hey Jarvis delete the file", "Hey Jarvis actually just show the file")
    await harness.configure()
    for _ in range(65):
        await harness.session.feed(VOICE)
    assert harness.session.segmenter.speaking
    await harness.session.partial_pending
    assert harness.named("transcript_partial")[0]["text"] == "delete the file"
    assert not harness.session.activated
    assert harness.session.awaiting_ack is None
    assert not harness.named("transcript")
    for _ in range(43):
        await harness.session.feed(SILENCE)
    await harness.session.pending
    assert harness.named("transcript")[0]["text"] == "actually just show the file"


@pytest.mark.parametrize("action", ["close", "approval", "reset"])
async def test_live_preview_lifetime_and_invalidation(action):
    harness = Harness("Hey Jarvis delete the file")
    await harness.configure()
    harness.gate = asyncio.Event()
    for _ in range(65):
        await harness.session.feed(VOICE)
    await asyncio.sleep(0)
    task = harness.session.partial_pending
    for _ in range(100):
        await harness.session.feed(VOICE)
    assert len(harness.audio) == 1
    if action == "close":
        assert harness.session.close() is task
    elif action == "approval":
        await harness.session.control({"type": "context", "awaiting_approval": True})
    else:
        await harness.session.control({"type": "reset"})
    harness.gate.set()
    await task
    assert not harness.named("transcript_partial")
    assert not harness.named("transcript")


async def test_idle_live_preview_never_exposes_household_speech():
    harness = Harness("Private household speech")
    await harness.configure()
    for _ in range(65):
        await harness.session.feed(VOICE)
    await harness.session.partial_pending
    assert not harness.named("transcript_partial")


@pytest.mark.parametrize(("text", "expected"), [
    ("Hey Jarvis, open my project.", "open my project."),
    ("HEY, JARVIS!", ""),
    ("  Hey Jarvis what's next?", "what's next?"),
    ("I said hey Jarvis open my project", None),
    ("Hey Jarvison open my project", None),
    ("Jarvis open my project", None),
    ("Hey Alice open my project", None),
])
def test_wake_phrase_is_complete_and_anchored(text, expected):
    assert extract_wake_command(text, "hey jarvis") == expected


@pytest.mark.parametrize("settings", [
    {"wake_phrase": []}, {"wake_phrase": "jarvis"},
    {"end_silence_ms": 499}, {"end_silence_ms": 2001}, {"end_silence_ms": True},
    {"followup_seconds": float("nan")}, {"followup_seconds": float("inf")},
    {"followup_seconds": -1}, {"followup_seconds": 31}, {"followup_seconds": False},
])
def test_configuration_rejects_invalid_values(settings):
    with pytest.raises(ValueError):
        ConversationConfig.parse(settings)


async def test_idle_transcription_never_leaks_and_wake_strips_only_prefix():
    harness = Harness("Private household conversation", "Hey Jarvis, give me a briefing.")
    await harness.configure()
    await harness.utterance()
    assert harness.named("transcript") == harness.named("wake") == []
    assert "Private" not in str(harness.events)
    await harness.utterance()
    assert harness.named("transcript")[0]["text"] == "give me a briefing."
    assert len(harness.named("wake")) == 1
    assert harness.session.state == "busy"
    with wave.open(io.BytesIO(harness.audio[0]), "rb") as recording:
        assert recording.getframerate() == 16000
        assert recording.getnchannels() == 1
        assert recording.getsampwidth() == 2
        pcm = recording.readframes(recording.getnframes())
    assert pcm.startswith(SILENCE * 7 + VOICE)  # pre-roll retains speech onset
    assert pcm.endswith(SILENCE * 10)


async def test_partial_transcription_is_visible_but_only_final_text_is_actionable():
    harness = Harness("Final command")

    async def transcribe(*, filename, content, on_partial=None):
        await on_partial({"text": "Final"})
        return {"text": "Final command"}

    harness.session.transcribe = transcribe
    await harness.configure()
    harness.session.activated = True
    harness.session.followup_until = harness.now + 10
    await harness.utterance()
    assert harness.named("transcript_partial")[0]["text"] == "Final"
    assert harness.named("transcript")[0]["text"] == "Final command"


async def test_wake_only_followup_and_followup_expiry():
    harness = Harness("Hey Alice", "What time is it?", "Not for Alice")
    await harness.configure(wake_phrase="hey alice", followup_seconds=5)
    await harness.utterance()
    assert harness.session.state == "listening"
    assert not harness.named("transcript")
    harness.now += 4
    await harness.utterance()
    transcript = harness.named("transcript")[0]
    await harness.session.control({"type": "ack", "turn_id": transcript["turn_id"], "accepted": True})
    await harness.session.control({"type": "context", "busy": False, "playback": True})
    harness.now += 100  # follow-up begins after the reply, not when speech was submitted
    await harness.session.control({"type": "context", "playback": False, "followup": True})
    assert harness.session.state == "listening"
    harness.now += 6
    await harness.session.tick()
    assert harness.session.state == "idle"
    assert not harness.session.activated
    await harness.utterance()
    assert len(harness.named("transcript")) == 1


async def test_utterance_started_before_window_expiry_remains_eligible():
    harness = Harness("Hey Jarvis", "Follow up")
    await harness.configure(followup_seconds=1)
    await harness.utterance()
    harness.gate = asyncio.Event()
    await harness.utterance(finish=False)
    harness.now += 30
    harness.gate.set()
    await harness.session.pending
    assert harness.named("transcript")[0]["text"] == "Follow up"


async def test_barge_in_survives_playback_context_changes():
    harness = Harness("Hey Jarvis, say hello", "Actually, stop and explain that.")
    await harness.configure()
    await harness.utterance()
    transcript = harness.named("transcript")[0]
    await harness.session.control({"type": "ack", "turn_id": transcript["turn_id"], "accepted": True})
    await harness.session.control({"type": "context", "busy": True, "playback": True})
    for _ in range(8):
        await harness.session.feed(VOICE)
    assert harness.named("speech_start")[-1]["interrupt"] is True
    await harness.session.control({"type": "context", "busy": False, "playback": False})
    for frame in [VOICE] * 12 + [SILENCE] * 43:
        await harness.session.feed(frame)
    await harness.session.pending
    assert harness.named("transcript")[-1]["text"] == "Actually, stop and explain that."


@pytest.mark.parametrize("control", [
    {"type": "reset"}, {"type": "context", "revision": 1},
    {"type": "context", "awaiting_approval": True},
])
async def test_invalidation_discards_late_results_without_parallel_inference(control):
    harness = Harness("Hey Jarvis, stale request")
    await harness.configure()
    harness.gate = asyncio.Event()
    await harness.utterance(finish=False)
    await asyncio.sleep(0)
    pending = harness.session.pending
    await harness.session.control(control)
    await harness.utterance(finish=False)
    assert harness.session.pending is pending
    assert len(harness.audio) == 1
    harness.gate.set()
    await pending
    assert not harness.named("transcript")
    assert not harness.named("wake")


async def test_close_keeps_inference_alive_but_never_emits_late_events():
    harness = Harness("Hey Jarvis, late result")
    await harness.configure()
    harness.gate = asyncio.Event()
    await harness.utterance(finish=False)
    pending = harness.session.close()
    count = len(harness.events)
    assert pending is not None and not pending.cancelled()
    harness.gate.set()
    await pending
    assert len(harness.events) == count


async def test_approval_blocks_microphone_commands_and_stale_ack_is_ignored():
    harness = Harness("Hey Jarvis, do a task", "yes, approve")
    await harness.configure()
    await harness.utterance()
    current = harness.session.awaiting_ack
    await harness.session.control({"type": "ack", "turn_id": "stale", "accepted": True})
    assert harness.session.awaiting_ack == current
    await harness.session.control({"type": "context", "awaiting_approval": True})
    await harness.utterance()
    assert harness.session.state == "approval"
    assert len(harness.audio) == len(harness.named("transcript")) == 1


async def test_packets_are_validated_and_no_audio_queues_while_waiting_for_ack():
    harness = Harness("Hey Jarvis, first command")
    with pytest.raises(ValueError):
        await harness.session.feed(SILENCE)
    await harness.configure()
    for pcm in (b"", b"x", VOICE * 11):
        with pytest.raises(ValueError):
            await harness.session.feed(pcm)
    await harness.utterance()
    await harness.utterance()
    assert len(harness.audio) == 1
    harness.now += 11
    await harness.session.tick()
    assert harness.session.state == "idle"
    assert harness.named("error")[0]["code"] == "ack_timeout"


def test_utterance_memory_is_bounded_and_silence_does_not_trigger():
    segmenter = SpeechSegmenter(500, FakeVad())
    for _ in range(5000):
        assert segmenter.feed_frame(SILENCE) == (False, None)
    assert len(segmenter.preroll) == 15
    segments = []
    for _ in range(MAX_UTTERANCE_MS // 20 + 10):
        _, pcm = segmenter.feed_frame(VOICE)
        if pcm:
            segments.append(pcm)
    assert len(segments) == 1
    assert len(segments[0]) <= MAX_UTTERANCE_MS // 20 * FRAME_BYTES


def test_process_lease_cannot_be_stolen_or_released_by_another_owner():
    owner = ConversationLease.acquire()
    assert owner is not None
    try:
        assert ConversationLease.acquire() is None
        ConversationLease.release(object())
        assert ConversationLease.acquire() is None
    finally:
        ConversationLease.release(owner)
    replacement = ConversationLease.acquire()
    assert replacement is not None
    ConversationLease.release(replacement)
