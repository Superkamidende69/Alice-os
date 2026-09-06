from __future__ import annotations

import argparse
import os
import sys
import uuid
from pathlib import Path

from voice_speech import text_for_speech, tts_to_wav


def add_ffmpeg_to_path() -> None:
    """Make a per-user winget FFmpeg install available to reference processing."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return
    packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    if not packages.is_dir():
        return
    for executable in packages.glob("Gyan.FFmpeg.Essentials*/**/bin/ffmpeg.exe"):
        ffmpeg_bin = str(executable.parent)
        if ffmpeg_bin not in os.environ.get("PATH", "").split(os.pathsep):
            os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local Alice speech reply with OpenVoice/MeloTTS.")
    parser.add_argument("--openvoice-root", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--speaker", default="EN-US")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--noise-scale", type=float, default=0.6)
    parser.add_argument("--noise-scale-w", type=float, default=0.8)
    parser.add_argument("--sdp-ratio", type=float, default=0.2)
    parser.add_argument("--reference", default="")
    parser.add_argument("--embedding-cache", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--cancel-path", default="")
    args = parser.parse_args()

    def check_cancel() -> None:
        if args.cancel_path and Path(args.cancel_path).exists():
            raise RuntimeError("Speech was interrupted.")

    check_cancel()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    add_ffmpeg_to_path()
    speech_text = text_for_speech(args.text)
    if not speech_text:
        raise ValueError("The reply did not contain speakable text.")
    root = Path(args.openvoice_root).resolve()
    sys.path.insert(0, str(root))
    import torch
    from melo.api import TTS

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model = TTS(language="EN_NEWEST", device=device)
    speaker_ids = model.hps.data.spk2id
    speaker_id = speaker_ids[args.speaker] if args.speaker in speaker_ids else next(iter(speaker_ids.values()))
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not args.reference:
        tts_to_wav(model, speech_text, speaker_id, output, args.speed, args.noise_scale, args.noise_scale_w, args.sdp_ratio, check_cancel)
        return

    reference = Path(args.reference).resolve()
    if not reference.is_file():
        raise FileNotFoundError("The selected voice reference was not found.")
    from openvoice import se_extractor
    from openvoice.api import ToneColorConverter

    checkpoint_root = root / "checkpoints_v2"
    converter = ToneColorConverter(str(checkpoint_root / "converter" / "config.json"), device=device)
    converter.load_ckpt(str(checkpoint_root / "converter" / "checkpoint.pth"))
    source_name = args.speaker.lower().replace("_", "-")
    source_embedding = checkpoint_root / "base_speakers" / "ses" / f"{source_name}.pth"
    if not source_embedding.is_file():
        raise FileNotFoundError(f"OpenVoice speaker embedding is missing: {source_embedding.name}")
    embedding_cache = Path(args.embedding_cache).resolve() if args.embedding_cache else None
    if embedding_cache and embedding_cache.is_file():
        target_embedding = torch.load(str(embedding_cache), map_location=device).to(device)
    else:
        target_dir = embedding_cache.parent / "processed" if embedding_cache else output.parent / "voice-cache"
        target_embedding, _ = se_extractor.get_se(str(reference), converter, target_dir=str(target_dir), vad=True)
        if embedding_cache:
            embedding_cache.parent.mkdir(parents=True, exist_ok=True)
            torch.save(target_embedding.detach().cpu(), str(embedding_cache))
    temporary = output.parent / f".{uuid.uuid4().hex}.wav"
    try:
        tts_to_wav(model, speech_text, speaker_id, temporary, args.speed, args.noise_scale, args.noise_scale_w, args.sdp_ratio, check_cancel)
        check_cancel()
        converter.convert(
            audio_src_path=str(temporary),
            src_se=torch.load(str(source_embedding), map_location=device),
            tgt_se=target_embedding,
            output_path=str(output),
            message="@AliceOS",
        )
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
