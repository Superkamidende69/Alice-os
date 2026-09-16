"""Bounded local speech segmentation and wake-gated conversation.

Audio and idle transcripts are transient. The caller supplies local transcription
and receives only commands spoken after a wake phrase or during an active turn.
This module never invokes an agent, executes tools, or writes conversation data.
"""

from __future__ import annotations

import asyncio
import io
import math
import re
import threading
import time
import wave
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import webrtcvad

SAMPLE_RATE = 16_000
FRAME_BYTES = 640
FRAME_MS = 20
MAX_UTTERANCE_MS = 15_000


@dataclass(frozen=True)
class ConversationConfig:
    wake_phrase: str = "hey jarvis"
    end_silence_ms: int = 700
    followup_seconds: float = 12

    @classmethod
    def parse(cls, message: dict[str, Any]) -> ConversationConfig:
        phrase = message.get("wake_phrase", "hey jarvis")
        silence = message.get("end_silence_ms", 700)
        followup = message.get("followup_seconds", 12)
        if not isinstance(phrase, str) or phrase not in {"hey alice", "hey jarvis"}:
            raise ValueError("Choose 'hey alice' or 'hey jarvis' as the wake phrase.")
        if type(silence) is not int or not 500 <= silence <= 2000:
            raise ValueError("end_silence_ms must be an integer between 500 and 2000.")
        if (
            type(followup) not in {int, float}
            or not math.isfinite(followup)
            or not 0 <= followup <= 30
        ):
            raise ValueError("followup_seconds must be between 0 and 30.")
        return cls(phrase, silence, float(followup))


def extract_wake_command(text: str, phrase: str) -> str | None:
    """Accept a complete wake phrase only at the beginning, never as a substring."""
    words = phrase.split()
    pattern = r"^[\s\W]*" + r"[\s,;:!?.-]+".join(map(re.escape, words)) + r"\b"
    match = re.match(pattern, text, re.IGNORECASE)
    if match is None:
        return None
    return text[match.end():].lstrip(" \t\r\n,;:!?.-—")


def pcm_to_wav(pcm: bytes) -> bytes:
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(SAMPLE_RATE)
            output.writeframes(pcm)
        return buffer.getvalue()


class ConversationLease:
    """One process-wide hands-free stream, including unfinished local inference."""

    _lock = threading.Lock()
    _owner: object | None = None

    @classmethod
    def acquire(cls) -> object | None:
        with cls._lock:
            if cls._owner is not None:
                return None
            cls._owner = object()
            return cls._owner

    @classmethod
    def release(cls, owner: object) -> None:
        with cls._lock:
            if cls._owner is owner:
                cls._owner = None


class SpeechSegmenter:
    """WebRTC VAD with 300 ms pre-roll and a hard 15 second utterance limit."""

    def __init__(self, end_silence_ms: int, vad: Any = None) -> None:
        self.vad = vad if vad is not None else webrtcvad.Vad(2)
        self.end_silence_frames = math.ceil(end_silence_ms / FRAME_MS)
        self.reset()

    def reset(self) -> None:
        self.recent: deque[bool] = deque(maxlen=10)
        self.preroll: deque[bytes] = deque(maxlen=15)
        self.frames: list[bytes] = []
        self.silent_frames = 0
        self.speaking = False

    def feed_frame(self, frame: bytes) -> tuple[bool, bytes | None]:
        voiced = self.vad.is_speech(frame, SAMPLE_RATE)
        self.recent.append(voiced)
        if not self.speaking:
            self.preroll.append(frame)
            if sum(self.recent) < 8:
                return False, None
            self.speaking = True
            self.frames = list(self.preroll)
            self.preroll.clear()
            self.silent_frames = 0
            return True, None
        self.frames.append(frame)
        self.silent_frames = 0 if voiced else self.silent_frames + 1
        if (
            self.silent_frames >= self.end_silence_frames
            or len(self.frames) * FRAME_MS >= MAX_UTTERANCE_MS
        ):
            # Keep a little trailing silence; Whisper does not need the full pause.
            trim = max(0, self.silent_frames - 10)
            frames = self.frames[:-trim] if trim else self.frames
            pcm = b"".join(frames)
            self.reset()
            return False, pcm
        return False, None


class HandsFreeConversation:
    def __init__(
        self,
        *,
        transcribe: Callable[..., Awaitable[dict[str, str]]],
        emit: Callable[[dict[str, Any]], Awaitable[None]],
        clock: Callable[[], float] = time.monotonic,
        vad: Any = None,
    ) -> None:
        self.config = ConversationConfig()
        self.segmenter = SpeechSegmenter(self.config.end_silence_ms, vad)
        self.transcribe = transcribe
        self.emit = emit
        self.clock = clock
        self.revision = 0
        self.generation = 0
        self.turn_sequence = 0
        self.closed = False
        self.configured = False
        self.busy = False
        self.playback = False
        self.awaiting_approval = False
        self.activated = False
        self.followup_until = 0.0
        self.pending: asyncio.Task[None] | None = None
        self.partial_pending: asyncio.Task[None] | None = None
        self.partial_after = 0.0
        self.awaiting_ack: str | None = None
        self.ack_deadline = 0.0
        self._capture: tuple[int, int, str, bool] | None = None
        self._capture_started_at = 0.0
        self._last_state = ""

    @property
    def state(self) -> str:
        if self.awaiting_approval:
            return "approval"
        if self.pending is not None:
            return "transcribing"
        if self.segmenter.speaking:
            return "capturing"
        if self.playback:
            return "speaking"
        if self.busy or self.awaiting_ack:
            return "busy"
        if self.followup_until > self.clock():
            return "listening"
        return "idle"

    async def send_state(self, *, force: bool = False) -> None:
        state = self.state
        if not self.closed and (force or state != self._last_state):
            self._last_state = state
            await self.emit({
                "event": "state", "state": state, "context_revision": self.revision,
                "followup_remaining_ms": max(0, round((self.followup_until - self.clock()) * 1000)),
            })

    def _invalidate(self) -> None:
        self.generation += 1
        self.segmenter.reset()
        self._capture = None
        self._capture_started_at = 0.0
        self.awaiting_ack = None
        self.activated = False
        self.followup_until = 0

    def _arm_followup(self) -> None:
        self.followup_until = self.clock() + self.config.followup_seconds

    async def control(self, message: dict[str, Any]) -> None:
        if self.closed:
            return
        kind = message.get("type")
        if kind == "configure":
            self.config = ConversationConfig.parse(message)
            self._invalidate()
            self.segmenter.end_silence_frames = math.ceil(self.config.end_silence_ms / FRAME_MS)
            self.configured = True
        elif kind == "reset":
            self._invalidate()
        elif kind == "context":
            revision = message.get("revision", self.revision)
            if type(revision) is not int or revision < self.revision:
                raise ValueError("Context revision must be a monotonically increasing integer.")
            for key in ("busy", "playback", "awaiting_approval", "followup"):
                if key in message and type(message[key]) is not bool:
                    raise ValueError(f"{key} must be true or false.")
            if revision != self.revision:
                self._invalidate()
                self.revision = revision
            approval = message.get("awaiting_approval", self.awaiting_approval)
            if approval and not self.awaiting_approval:
                self._invalidate()
            self.awaiting_approval = approval
            self.busy = message.get("busy", self.busy)
            self.playback = message.get("playback", self.playback)
            if self.busy or self.playback or self.awaiting_approval:
                self.followup_until = 0
            elif message.get("followup") and self.activated:
                self._arm_followup()
        elif kind == "ack":
            if type(message.get("accepted")) is not bool:
                raise ValueError("Acknowledgements require accepted: true or false.")
            if (
                message.get("turn_id") != self.awaiting_ack
                or message.get("context_revision", self.revision) != self.revision
            ):
                return
            self.awaiting_ack = None
            if message["accepted"]:
                self.busy = True
                self.followup_until = 0
            elif self.activated and not (self.busy or self.playback or self.awaiting_approval):
                self._arm_followup()
        else:
            raise ValueError("Send configure, context, ack, or reset controls.")
        await self.send_state(force=True)

    async def tick(self) -> None:
        if self.awaiting_ack and self.clock() >= self.ack_deadline:
            self.awaiting_ack = None
            self._invalidate()
            await self.emit({
                "event": "error", "code": "ack_timeout", "recoverable": True,
                "message": "The voice request was not accepted. Say the wake phrase to try again.",
            })
        if (
            self.activated and not (self.busy or self.playback or self.awaiting_ack)
            and self.pending is None and not self.segmenter.speaking
            and self.followup_until <= self.clock()
        ):
            self.activated = False
        await self.send_state()

    async def feed(self, pcm: bytes) -> None:
        if not pcm or len(pcm) % FRAME_BYTES or len(pcm) > FRAME_BYTES * 10:
            raise ValueError("Send 20–200 ms of 16 kHz mono PCM16 audio.")
        if not self.configured:
            raise ValueError("Configure hands-free conversation before sending audio.")
        await self.tick()
        if self.closed or self.pending is not None or self.awaiting_approval or self.awaiting_ack:
            return
        for offset in range(0, len(pcm), FRAME_BYTES):
            started, utterance = self.segmenter.feed_frame(pcm[offset:offset + FRAME_BYTES])
            if started:
                self.turn_sequence += 1
                turn = f"{self.generation}-{self.turn_sequence}"
                eligible = self.activated and (
                    self.busy or self.playback or self.followup_until > self.clock()
                )
                self._capture = (self.generation, self.revision, turn, eligible)
                self._capture_started_at = self.clock()
                self.partial_after = self.clock()
                await self.emit({
                    "event": "speech_start", "turn_id": turn,
                    "context_revision": self.revision,
                    "interrupt": bool(eligible and (self.busy or self.playback)),
                })
                await self.send_state()
            if utterance is not None and self._capture is not None:
                capture = self._capture
                self._capture = None
                self.pending = asyncio.create_task(self._transcribe(utterance, capture))
                await self.send_state()
                break  # Never queue or retain audio behind a transcription.
        if (self._capture is not None and self.segmenter.speaking
                and len(self.segmenter.frames) * FRAME_MS >= 1200
                and self.segmenter.silent_frames < 10
                and self.clock() >= self.partial_after
                and (self.partial_pending is None or self.partial_pending.done())):
            self.partial_after = self.clock() + 1.2
            self.partial_pending = asyncio.create_task(self._preview(
                b"".join(self.segmenter.frames), self._capture))

    async def _preview(self, pcm: bytes, capture: tuple[int, int, str, bool]) -> None:
        generation, revision, turn, eligible = capture
        try:
            result = await self.transcribe(filename="handsfree.wav", content=pcm_to_wav(pcm))
            if (self.closed or generation != self.generation or self.awaiting_approval
                    or self._capture != capture):
                return
            text = str(result.get("text", "")).strip()
            command = extract_wake_command(text, self.config.wake_phrase)
            if command is not None:
                text = command
            elif not eligible:
                return
            if text:
                await self.emit({"event": "transcript_partial", "text": text,
                                 "turn_id": turn, "context_revision": revision})
        except Exception:
            pass  # A preview failure must not prevent authoritative final decoding.
        finally:
            # Slow CPUs never build a queue of obsolete snapshots.
            self.partial_after = self.clock() + 1.2

    async def _transcribe(self, pcm: bytes, capture: tuple[int, int, str, bool]) -> None:
        generation, revision, turn, eligible = capture
        started_at = time.monotonic()
        capture_ms = round(max(0, (self.clock() - self._capture_started_at) * 1000))
        try:
            if self.partial_pending is not None:
                await asyncio.shield(self.partial_pending)
            if self.closed or generation != self.generation or self.awaiting_approval:
                return
            async def partial(result: dict[str, str]) -> None:
                text = str(result.get("text", "")).strip()
                if text and eligible and not self.closed and generation == self.generation:
                    await self.emit({
                        "event": "transcript_partial", "text": text,
                        "turn_id": turn, "context_revision": revision,
                    })

            result = await self.transcribe(
                filename="handsfree.wav", content=pcm_to_wav(pcm), on_partial=partial,
            )
            if self.closed or generation != self.generation or self.awaiting_approval:
                return
            text = str(result.get("text", "")).strip()
            if not text:
                return
            command = extract_wake_command(text, self.config.wake_phrase)
            if command is not None:
                self.activated = True
                await self.emit({"event": "wake", "turn_id": turn, "context_revision": revision})
                self._arm_followup()
                text = command
            elif not eligible:
                return  # Idle speech is never emitted, stored, or sent to a provider.
            if text:
                self.awaiting_ack = turn
                self.ack_deadline = self.clock() + 10
                self.followup_until = 0
                await self.emit({
                    "event": "transcript", "text": text,
                    "recognition_ms": round((time.monotonic() - started_at) * 1000),
                    "capture_ms": capture_ms,
                    "turn_id": turn, "context_revision": revision,
                })
        except asyncio.CancelledError:
            raise
        except Exception:
            if not self.closed and generation == self.generation:
                # No exception contents: local worker errors can contain paths/audio text.
                await self.emit({
                    "event": "error", "code": "transcription_failed", "recoverable": True,
                    "message": "Local speech recognition failed. Try again or check Voice setup.",
                })
        finally:
            self.pending = None
            self.segmenter.reset()
            if not self.closed:
                await self.send_state()

    def close(self) -> asyncio.Task[None] | None:
        """Invalidate late results, but keep the worker's one outstanding call alive.

        Cancelling an asyncio.to_thread call would not stop its worker thread and
        could release the global lease while inference is still running.
        """
        self.closed = True
        self._invalidate()
        return self.pending or self.partial_pending
