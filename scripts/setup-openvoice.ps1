[CmdletBinding()]
param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$openVoiceRoot = Join-Path $projectRoot "tools\OpenVoice"
$openVoicePython = Join-Path $openVoiceRoot ".venv\Scripts\python.exe"

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

if (-not (Test-Path -LiteralPath $openVoiceRoot -PathType Container)) {
    git clone --depth 1 https://github.com/myshell-ai/OpenVoice.git $openVoiceRoot
}

if (-not $Python) {
    $candidate = & py -3.10 -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0) { $Python = $candidate.Trim() }
}
if (-not $Python -or -not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "OpenVoice needs Python 3.10. Install a current Python 3.10 release, then rerun this script or pass -Python C:\Path\python.exe. Alice itself stays on its own Python version."
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
if (-not (Get-Command "ffmpeg" -ErrorAction SilentlyContinue)) {
    Write-Warning "FFmpeg is not on PATH. Install it (for example: winget install --id Gyan.FFmpeg.Essentials --exact --scope user) before using MP3/M4A voice references."
}
Invoke-OpenVoiceCommand "Downloading OpenVoice V2 checkpoints" { & $openVoicePython -c "from huggingface_hub import snapshot_download; snapshot_download('myshell-ai/OpenVoiceV2', local_dir=r'$openVoiceRoot\checkpoints_v2')" }
Invoke-OpenVoiceCommand "Checking speech and voice-cloning imports" { & $openVoicePython -c "from openvoice.api import ToneColorConverter; from openvoice import se_extractor; from melo.api import TTS; print('OpenVoice runtime: OK')" }

Write-Host "OpenVoice is ready. Restart Alice, then turn on Speak replies in the message box."
