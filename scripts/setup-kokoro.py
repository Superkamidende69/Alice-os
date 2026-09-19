"""Install optional local Kokoro speech without changing Alice/OpenVoice dependencies."""
import argparse
import hashlib
import subprocess
import sys
import urllib.request
import venv
from pathlib import Path

FILES = {
    "kokoro-v1.0.onnx": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "tools/kokoro"
    root.mkdir(parents=True, exist_ok=True)
    python = root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not args.models_only:
        if not python.is_file():
            venv.EnvBuilder(with_pip=True).create(root / ".venv")
        subprocess.run([str(python), "-m", "pip", "install", "kokoro-onnx==0.6.1", "soundfile==0.13.1"], check=True)
    for name, expected in FILES.items():
        target = root / name
        if target.is_file():
            with target.open("rb") as handle:
                if hashlib.file_digest(handle, "sha256").hexdigest() == expected:
                    continue
        partial = target.with_suffix(target.suffix + ".download")
        print(f"Downloading {name}...", flush=True)
        try:
            urllib.request.urlretrieve(f"https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/{name}", partial)
            with partial.open("rb") as handle:
                if hashlib.file_digest(handle, "sha256").hexdigest() != expected:
                    raise RuntimeError(f"Checksum mismatch: {name}")
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
    print("Kokoro installed. Select a Kokoro voice in Voice Studio to try it; the current voice is unchanged.")


if __name__ == "__main__":
    main()
