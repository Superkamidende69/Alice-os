[CmdletBinding()]
param(
    [string]$Python = "",

    [string]$OpenVoiceRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$openVoiceRoot = if ($OpenVoiceRoot) { [IO.Path]::GetFullPath($OpenVoiceRoot) } else { Join-Path $projectRoot "tools\OpenVoice" }
$openVoicePython = Join-Path $openVoiceRoot ".venv\Scripts\python.exe"

function Update-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = @($machinePath, $userPath, $env:Path | Where-Object { $_ }) -join ";"
}

function Install-WingetPackage {
    param([string]$Id, [string]$Name)
    $winget = Get-Command "winget.exe" -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "$Name is required, but Windows App Installer (winget) is unavailable. Install App Installer and rerun setup."
    }
    Write-Host "Installing $Name..."
    & $winget.Source install --id $Id --exact --source winget --scope user --disable-interactivity `
        --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Could not install $Name (exit code $LASTEXITCODE)." }
    Update-ProcessPath
}

function Find-Python310 {
    if ($Python -and (Test-Path -LiteralPath $Python -PathType Leaf)) { return $Python }
    $launcher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($launcher) {
        $candidate = & $launcher.Source -3.10 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) { return $candidate.Trim() }
    }
    foreach ($candidate in @(
        (Join-Path $env:LocalAppData "Programs\Python\Python310\python.exe"),
        "C:\Program Files\Python310\python.exe"
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    Install-WingetPackage -Id "Python.Python.3.10" -Name "Python 3.10 for OpenVoice"
    foreach ($candidate in @(
        (Join-Path $env:LocalAppData "Programs\Python\Python310\python.exe"),
        "C:\Program Files\Python310\python.exe"
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw "Python 3.10 was installed but could not be found. Open a new PowerShell window and rerun setup."
}

function Invoke-OpenVoiceCommand {
    param(
        [string]$Label,
        [scriptblock]$Command
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed (exit code $LASTEXITCODE)."
    }
}

$Python = Find-Python310

$git = Get-Command "git.exe" -ErrorAction SilentlyContinue
if (-not $git) {
    Install-WingetPackage -Id "Git.Git" -Name "Git for OpenVoice and MeloTTS"
    $git = Get-Command "git.exe" -ErrorAction SilentlyContinue
}
if (-not $git) { throw "Git was installed but could not be found. Open a new PowerShell window and rerun setup." }

if (-not (Test-Path -LiteralPath $openVoiceRoot -PathType Container)) {
    & $git.Source clone --depth 1 https://github.com/myshell-ai/OpenVoice.git $openVoiceRoot
    if ($LASTEXITCODE -ne 0) { throw "Downloading the OpenVoice source failed (exit code $LASTEXITCODE)." }
}

& $Python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) { throw "OpenVoice requires Python 3.10 for its pinned dependencies." }

if (-not (Test-Path -LiteralPath $openVoicePython -PathType Leaf)) {
    Invoke-OpenVoiceCommand "Creating the OpenVoice virtual environment" { & $Python -m venv (Join-Path $openVoiceRoot ".venv") }
}
else {
    Write-Host "Reusing the existing OpenVoice virtual environment."
}
# librosa 0.9 (required by OpenVoice V2) still imports pkg_resources, removed
# from the newest setuptools builds. Keep the last compatible setuptools line.
Invoke-OpenVoiceCommand "Updating OpenVoice installer tools" { & $openVoicePython -m pip install --upgrade "pip>=25,<26" "setuptools<81" wheel }
if (Get-Command "nvidia-smi" -ErrorAction SilentlyContinue) {
    Write-Host "Installing CUDA-enabled PyTorch for OpenVoice..."
    Invoke-OpenVoiceCommand "Installing CUDA PyTorch" { & $openVoicePython -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 }
}
else {
    Write-Host "Installing CPU PyTorch for OpenVoice..."
    Invoke-OpenVoiceCommand "Installing CPU PyTorch" { & $openVoicePython -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu }
}
# The upstream package pins an obsolete PyAV build that cannot compile on modern
# Windows.  The local OpenVoice source is used directly by Alice's runner, so
# install it without that legacy dependency chain and install compatible runtime
# pieces explicitly instead.
Invoke-OpenVoiceCommand "Registering the local OpenVoice source" { & $openVoicePython -m pip install --editable $openVoiceRoot --no-deps }
Invoke-OpenVoiceCommand "Installing MeloTTS and OpenVoice runtime packages" { & $openVoicePython -m pip install "git+https://github.com/myshell-ai/MeloTTS.git" huggingface_hub "faster-whisper>=1.1,<2" "whisper-timestamped>=1.15,<2" "regex==2024.11.6" "wavmark==0.0.3" }
# MeloTTS includes unidic-lite, which works on Windows. Its optional full
# unidic package redirects MeCab to a dictionary that needs a Unix-only helper.
& $openVoicePython -m pip uninstall --yes unidic | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Removing the incompatible full UniDic package failed (exit code $LASTEXITCODE)." }
$nltkData = Join-Path $openVoiceRoot ".venv\nltk_data"
New-Item -ItemType Directory -Force -Path $nltkData | Out-Null
Invoke-OpenVoiceCommand "Downloading MeloTTS English language data" { & $openVoicePython -c "import nltk; nltk.download('averaged_perceptron_tagger_eng', download_dir=r'$nltkData', quiet=True)" }
if (-not (Get-Command "ffmpeg.exe" -ErrorAction SilentlyContinue)) {
    Install-WingetPackage -Id "Gyan.FFmpeg.Essentials" -Name "FFmpeg for voice references"
    if (-not (Get-Command "ffmpeg.exe" -ErrorAction SilentlyContinue)) {
        Write-Warning "FFmpeg was installed but is not available in this terminal yet. MP3/M4A voice references may need a new terminal."
    }
}
Invoke-OpenVoiceCommand "Downloading OpenVoice V2 checkpoints" { & $openVoicePython -c "from huggingface_hub import snapshot_download; snapshot_download('myshell-ai/OpenVoiceV2', local_dir=r'$openVoiceRoot\checkpoints_v2')" }
New-Item -ItemType Directory -Force -Path (Join-Path $openVoiceRoot "models\whisper") | Out-Null
Invoke-OpenVoiceCommand "Downloading the local Whisper dictation model" { & $openVoicePython -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8', download_root=r'$openVoiceRoot\models\whisper'); print('Whisper base model: OK')" }
Invoke-OpenVoiceCommand "Checking speech and voice-cloning imports" { & $openVoicePython -c "from openvoice.api import ToneColorConverter; from openvoice import se_extractor; from melo.api import TTS; print('OpenVoice runtime: OK')" }

Write-Host "OpenVoice is ready. Restart Alice, then turn on Speak replies in the message box."
