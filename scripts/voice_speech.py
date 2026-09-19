"""Shared speech preparation for both OpenVoice entry points (Python 3.10+)."""

import re
import unicodedata
import uuid
import wave
from array import array
from pathlib import Path
from typing import Callable

_SPOKEN_REPLACEMENTS = (
    (r"\be\.g\.(?!\w)", "for example"),
    (r"\bi\.e\.(?!\w)", "that is"),
    (r"\bDr\.", "Doctor"),
    (r"\bProf\.", "Professor"),
    (r"\bMr\.", "Mister"),
    (r"\bMrs\.", "Missus"),
    (r"\bMs\.", "Miss"),
)
_NON_TERMINAL_ABBREVIATIONS = {
    "dr.", "prof.", "mr.", "mrs.", "ms.", "sr.", "jr.", "st.", "vs.", "etc.", "e.g.", "i.e.",
}


def text_for_speech(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " See the code in the chat. ", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    replacements = str.maketrans({
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": ", ", "—": ", ", "…": "...",
    })
    text = unicodedata.normalize("NFKC", text).translate(replacements)
    for pattern, spoken in _SPOKEN_REPLACEMENTS:
        text = re.sub(pattern, spoken, text, flags=re.IGNORECASE)
    text = text.replace("&", " and ").replace("@", " at ")
    # Preserve whitespace before stripping control characters: never join words
    # on opposite sides of a line break. Melo's English model expects prose.
    text = re.sub(r"\s+", " ", text)
    text = "".join(c for c in text if unicodedata.category(c) not in {"So", "Sk", "Cs", "Cc"})
    text = re.sub(r"[^A-Za-z0-9\s.,!?;:'\"()\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lstrip(".,!?;:- ")


def _is_chunk_boundary(text: str, index: int) -> bool:
    """Return whether punctuation at *index* can safely end a spoken chunk."""
    marker = text[index]
    if marker not in ".!?;,:":
        return False
    following = index + 1
    while following < len(text) and text[following] in "\"'’”)]}":
        following += 1
    if following < len(text) and not text[following].isspace():
        # A comma without a following space still separates clauses, but not
        # thousands or decimal separators such as 1,000 and 3,14.
        if marker != "," or (index > 0 and text[index - 1].isdigit() and text[index + 1].isdigit()):
            return False
    if marker != ".":
        return True
    word_start = text.rfind(" ", 0, index) + 1
    word = text[word_start:index + 1].casefold().lstrip("\"'‘“(")
    # Do not introduce an unnatural full pause after titles, initials, or
    # abbreviations such as "e.g." when a response is split for inference.
    return word not in _NON_TERMINAL_ABBREVIATIONS and not re.fullmatch(r"(?:[a-z]\.){1,4}", word)


def speech_chunks(text: str, limit: int = 240) -> list[str]:
    """Split at real punctuation even in short replies so pauses are explicit."""
    if limit < 1:
        raise ValueError("Speech chunk limit must be positive.")
    chunks = []
    remaining = text.strip()
    while remaining:
        window = remaining[:limit + 1]
        boundaries = [index for index in range(len(window)) if _is_chunk_boundary(window, index)]
        cut = boundaries[0] + 1 if boundaries else 0
        if cut:
            while cut < len(remaining) and remaining[cut] in "\"'’”)]}":
                cut += 1
        elif len(remaining) <= limit:
            cut = len(remaining)
        else:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    return chunks


def pause_after(text: str) -> float:
    """Wall-clock punctuation pauses, including the end of streamed audio clips."""
    ending = text.rstrip().rstrip("\"'’”)]}")
    if ending.endswith("..."):
        return 0.40
    if ending.endswith(("?", "!")):
        return 0.34
    if ending.endswith(".") and _is_chunk_boundary(ending, len(ending) - 1):
        return 0.32
    if ending.endswith((";", ":")):
        return 0.22
    if ending.endswith(","):
        return 0.16
    return 0.04


def trim_padding(audio: bytes, channels: int, sample_width: int, rate: int) -> bytes:
    """Remove long silent margins, keeping 30 ms around quiet consonants."""
    if sample_width != 2 or not audio:
        return audio
    samples = array("h")
    samples.frombytes(audio)
    import sys
    if sys.byteorder != "little":
        samples.byteswap()
    first = next((i for i, value in enumerate(samples) if abs(value) > 32), None)
    if first is None:
        return audio
    last = len(samples) - next(i for i, value in enumerate(reversed(samples)) if abs(value) > 32)
    pad = int(rate * .03) * channels
    minimum = int(rate * .12) * channels
    start = max(0, (first // channels) * channels - pad) if first > minimum else 0
    end = min(len(samples), ((last + channels - 1) // channels) * channels + pad) if len(samples) - last > minimum else len(samples)
    return audio[start * sample_width:end * sample_width]


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
                    combined.writeframes(trim_padding(source.readframes(source.getnframes()), parameters.nchannels, parameters.sampwidth, parameters.framerate))
                    # Include the last pause: browser streaming often requests
                    # just one sentence per WAV. Playback speed never compresses
                    # these pauses because silence is added after synthesis.
                    pause = pause_after(chunks[index])
                    sample = b"\x80" if parameters.sampwidth == 1 else bytes(parameters.sampwidth)
                    combined.writeframes(sample * parameters.nchannels * int(parameters.framerate * pause))
    finally:
        for part in parts:
            part.unlink(missing_ok=True)
