"""Shared speech preparation for both OpenVoice entry points (Python 3.10+)."""

import re
import unicodedata
import uuid
import wave
from pathlib import Path
from typing import Callable


def text_for_speech(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " See the code in the chat. ", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    replacements = str.maketrans({
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": ", ", "—": ", ", "…": "...",
    })
    text = unicodedata.normalize("NFKC", text).translate(replacements)
    # Preserve whitespace before stripping control characters: never join words
    # on opposite sides of a line break. Melo's English model expects prose.
    text = re.sub(r"\s+", " ", text)
    text = "".join(c for c in text if unicodedata.category(c) not in {"So", "Sk", "Cs", "Cc"})
    text = re.sub(r"[^A-Za-z0-9\s.,!?;:'\"()\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lstrip(".,!?;:- ")


def speech_chunks(text: str, limit: int = 240) -> list[str]:
    """Prefer complete sentences/clauses; bound inference time on long replies."""
    chunks = []
    remaining = text.strip()
    while len(remaining) > limit:
        window = remaining[:limit + 1]
        boundaries = list(re.finditer(r"[.!?;,:](?=\s)", window))
        cut = next((m.end() for m in reversed(boundaries) if m.end() >= limit // 3), 0)
        if not cut:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def tts_to_wav(
    model: object, text: str, speaker_id: int, output: Path, speed: float,
    noise_scale: float, noise_scale_w: float, sdp_ratio: float,
    check_cancel: Callable[[], None] = lambda: None,
) -> None:
    chunks = speech_chunks(text)
    if not chunks:
        raise ValueError("The reply did not contain speakable text.")
    parts = []
    try:
        for chunk in chunks:
            check_cancel()
            part = output.parent / f".{output.stem}-{uuid.uuid4().hex}.wav"
            parts.append(part)
            model.tts_to_file(
                chunk, speaker_id, str(part), speed=speed,
                noise_scale=noise_scale, noise_scale_w=noise_scale_w, sdp_ratio=sdp_ratio,
            )
            check_cancel()
        with wave.open(str(parts[0]), "rb") as first:
            parameters = first.getparams()
        with wave.open(str(output), "wb") as combined:
            combined.setparams(parameters)
            for index, part in enumerate(parts):
                check_cancel()
                with wave.open(str(part), "rb") as source:
                    if source.getparams()[:3] != parameters[:3]:
                        raise RuntimeError("OpenVoice generated incompatible speech segments.")
                    if index:
                        # Small punctuation-aware pauses between internal segments.
                        pause = 0.10 if chunks[index - 1].endswith((".", "!", "?")) else 0.045
                        sample = b"\x80" if parameters.sampwidth == 1 else bytes(parameters.sampwidth)
                        combined.writeframes(sample * parameters.nchannels * int(parameters.framerate * pause))
                    combined.writeframes(source.readframes(source.getnframes()))
    finally:
        for part in parts:
            part.unlink(missing_ok=True)
