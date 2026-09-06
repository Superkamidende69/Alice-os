"""Local WebRTC speech activity detection; no transcription or audio retention."""

from collections import deque

import webrtcvad


class SpeechActivityDetector:
    sample_rate = 16_000
    frame_bytes = 640  # 20 ms, mono signed 16-bit PCM

    def __init__(self) -> None:
        self.vad = webrtcvad.Vad(2)
        self.recent: deque[bool] = deque(maxlen=10)
        self.speaking = False
        self.silent_frames = 0

    def feed(self, pcm: bytes) -> list[str]:
        if not pcm or len(pcm) % self.frame_bytes or len(pcm) > self.frame_bytes * 10:
            raise ValueError("Send 20–200 ms of 16 kHz mono PCM16 audio.")
        events = []
        for offset in range(0, len(pcm), self.frame_bytes):
            voiced = self.vad.is_speech(pcm[offset:offset + self.frame_bytes], self.sample_rate)
            self.recent.append(voiced)
            if not self.speaking and sum(self.recent) >= 8:
                self.speaking = True
                self.silent_frames = 0
                events.append("speech_start")
            elif self.speaking:
                self.silent_frames = 0 if voiced else self.silent_frames + 1
                if self.silent_frames >= 25:
                    self.speaking = False
                    self.recent.clear()
                    events.append("speech_end")
        return events
