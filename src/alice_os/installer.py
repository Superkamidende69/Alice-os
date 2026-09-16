"""Console installer entry point used by AliceOS-Installer.exe."""
from __future__ import annotations

import getpass
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from .config import default_data_dir
from .installation import initialize_installation
from .paths import resource_root


def _install_app() -> Path:
    source = resource_root() / "app"
    if not source.is_dir():
        raise RuntimeError("The installer does not contain the AliceOS application bundle.")
    target = Path.home() / "AppData" / "Local" / "Programs" / "AliceOS"
    target.mkdir(parents=True, exist_ok=True)
    print(f"Installing AliceOS application to {target}...")
    shutil.copytree(source, target, dirs_exist_ok=True)
    executable = target / "AliceOS.exe"
    if not executable.is_file():
        raise RuntimeError("The installed AliceOS.exe is missing.")
    return executable


def _create_shortcuts(executable: Path) -> None:
    desktop = Path.home() / "Desktop" / "Alice OS.lnk"
    programs = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    start_menu = programs / "Alice OS.lnk"
    script = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$paths = @('{desktop}', '{start_menu}'); "
        "foreach ($path in $paths) { $folder = Split-Path $path; New-Item -ItemType Directory -Force -Path $folder | Out-Null; "
        "$link = $shell.CreateShortcut($path); "
        f"$link.TargetPath = '{executable}'; $link.WorkingDirectory = '{executable.parent}'; "
        "$link.Description = 'Alice OS'; $link.Save() }"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], check=True)


def _write_uninstaller(executable: Path, data_dir: Path) -> None:
    """Write a self-removing uninstaller with an explicit data-deletion choice."""
    app_dir = executable.parent
    def escape(value: object) -> str:
        return str(value).replace("'", "''")

    script = app_dir / "Uninstall AliceOS.ps1"
    script.write_text(
        "[CmdletBinding()]\r\n"
        "$ErrorActionPreference = 'Stop'\r\n"
        f"$appDir = '{escape(app_dir)}'\r\n"
        f"$dataDir = '{escape(data_dir)}'\r\n"
        "Write-Host 'This removes AliceOS and its shortcuts.'\r\n"
        "Write-Host 'Your conversations, models, account credentials, and OpenVoice files are kept by default.'\r\n"
        "$removeData = Read-Host 'Type DELETE to also permanently remove all Alice data'\r\n"
        "Remove-Item -LiteralPath (Join-Path $env:USERPROFILE 'Desktop\\Alice OS.lnk') -Force -ErrorAction SilentlyContinue\r\n"
        "Remove-Item -LiteralPath (Join-Path $env:APPDATA 'Microsoft\\Windows\\Start Menu\\Programs\\Alice OS.lnk') -Force -ErrorAction SilentlyContinue\r\n"
        "if ($removeData -ceq 'DELETE' -and (Test-Path -LiteralPath $dataDir)) {\r\n"
        "  Remove-Item -LiteralPath $dataDir -Recurse -Force\r\n"
        "  Write-Host 'Alice data was removed.'\r\n"
        "} else { Write-Host 'Alice data was kept.' }\r\n"
        "$cleanup = Join-Path $env:TEMP ('alice-uninstall-' + [guid]::NewGuid().ToString() + '.ps1')\r\n"
        "Set-Content -LiteralPath $cleanup -Value \"Start-Sleep -Seconds 2; Remove-Item -LiteralPath '$appDir' -Recurse -Force\" -Encoding UTF8\r\n"
        "Start-Process powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $cleanup) -WindowStyle Hidden\r\n"
        "Write-Host 'AliceOS was removed.'\r\n"
        "Read-Host 'Press Enter to close' | Out-Null\r\n",
        encoding="utf-8",
    )
    (app_dir / "Uninstall AliceOS.cmd").write_text(
        "@echo off\r\npowershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File \"%~dp0Uninstall AliceOS.ps1\"\r\n",
        encoding="utf-8",
    )


def _download_llama(data_dir: Path) -> None:
    target = data_dir / "runtimes" / "llama.cpp" / "bin3"
    if (target / "llama-server.exe").is_file():
        print("llama.cpp is already installed.")
        return
    print("Downloading llama.cpp backend...")
    request = urllib.request.Request(
        "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest",
        headers={"User-Agent": "AliceOS-Installer"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        assets = json.load(response).get("assets", [])
    cuda = shutil.which("nvidia-smi") is not None
    asset = next((a for a in assets if cuda and "win-cuda" in a["name"] and a["name"].endswith("x64.zip")), None)
    asset = asset or next((a for a in assets if "win-avx2" in a["name"] and a["name"].endswith("x64.zip")), None)
    if not asset:
        raise RuntimeError("No supported Windows llama.cpp release asset was found.")
    with tempfile.TemporaryDirectory(prefix="alice-llama-") as temporary:
        archive = Path(temporary) / "llama.zip"
        urllib.request.urlretrieve(asset["browser_download_url"], archive)
        with zipfile.ZipFile(archive) as bundle:
            server = next((name for name in bundle.namelist() if name.endswith("/llama-server.exe")), "")
            if not server:
                raise RuntimeError("The llama.cpp archive did not include llama-server.exe.")
            parent = server.rsplit("/", 1)[0] + "/"
            target.mkdir(parents=True, exist_ok=True)
            for member in bundle.infolist():
                if member.filename.startswith(parent) and not member.is_dir():
                    destination = target / member.filename[len(parent):]
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(member) as source, destination.open("wb") as output:
                        shutil.copyfileobj(source, output)


def main() -> None:
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Alice OS Installer\n\nRun without arguments to install llama.cpp and OpenVoice, then create Alice's administrator account.")
        return
    print("Alice OS Installer\n")
    default = default_data_dir()
    raw = input(f"Data directory [{default}]: ").strip()
    data_dir = Path(raw).expanduser() if raw else default
    if (data_dir / "network-auth.json").is_file():
        print("Existing Alice account found; keeping its data and credentials.")
    else:
        username = input("Administrator username: ").strip()
        password = getpass.getpass("Administrator password (at least 12 characters): ")
        if password != getpass.getpass("Confirm administrator password: "):
            raise SystemExit("Passwords do not match.")
        data_dir = initialize_installation(data_dir, username, password)
    executable = _install_app()
    _download_llama(data_dir)
    print("Preparing OpenVoice (this can take several minutes)...")
    script = resource_root() / "scripts" / "setup-openvoice.ps1"
    result = subprocess.run([
        "powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
        "-OpenVoiceRoot", str(data_dir / "runtimes" / "OpenVoice"),
    ])
    if result.returncode:
        raise SystemExit(result.returncode)
    _create_shortcuts(executable)
    _write_uninstaller(executable, data_dir)
    print("\nInstallation complete. Desktop and Start Menu shortcuts were created.")
    if input("Start Alice now? [Y/n]: ").strip().casefold() not in {"n", "no"}:
        subprocess.Popen([str(executable)])


if __name__ == "__main__":
    main()
