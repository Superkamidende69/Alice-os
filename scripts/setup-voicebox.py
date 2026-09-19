"""Extract the official Windows Voicebox runtime without changing Alice's venv."""
import hashlib
import os
import subprocess
from pathlib import Path
from urllib.request import urlopen

VERSION = "0.5.0"
SHA256 = "6242007dcee2c7127b687873c0d97d02958d6d5b3bb304dca70439ecf595cdd0"
URL = f"https://github.com/jamiepine/voicebox/releases/download/v{VERSION}/Voicebox_{VERSION}_x64_en-US.msi"


def verified(path):
    if not path.is_file():
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == SHA256


def main():
    if os.name != "nt":
        raise SystemExit("Use Voicebox's official installation instructions on macOS/Linux.")
    root = Path(__file__).resolve().parents[1] / "tools" / "voicebox-runtime"
    root.mkdir(parents=True, exist_ok=True)
    installer = root / f"Voicebox_{VERSION}.msi"
    if not verified(installer):
        temporary = installer.with_suffix(".download")
        print(f"Downloading Voicebox {VERSION} (543 MB)...", flush=True)
        digest = hashlib.sha256()
        with urlopen(URL, timeout=60) as response, temporary.open("wb") as output:
            count = 0
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
                count += len(chunk)
                if count % (50 * 1024 * 1024) == 0:
                    print(f"Downloaded {count // (1024 * 1024)} MB", flush=True)
        if digest.hexdigest() != SHA256:
            raise SystemExit("Voicebox checksum mismatch; runtime was not extracted.")
        temporary.replace(installer)
    print("Verified official release checksum. Extracting private runtime...", flush=True)
    subprocess.run(["msiexec.exe", "/a", str(installer), "/qn", f"TARGETDIR={root / 'app'}", "/L*v", str(root / "setup.log")], check=True)
    executables = list((root / "app").rglob("voicebox-server*.exe"))
    if not executables:
        raise SystemExit(f"No backend found after extraction. See {root / 'setup.log'}")
    print("Ready: " + str(executables[0]), flush=True)


if __name__ == "__main__":
    main()
