[CmdletBinding()]
param(
    [switch]$WithoutDev
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$venvRoot = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"

function Find-CompatiblePython {
    $candidates = @()

    $launcher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($launcher) {
        $candidates += [pscustomobject]@{
            Executable = $launcher.Source
            Prefix = @("-3")
            Label = "py -3"
        }
    }

    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            $candidates += [pscustomobject]@{
                Executable = $command.Source
                Prefix = @()
                Label = $name
            }
        }
    }

    foreach ($candidate in $candidates) {
        & $candidate.Executable @($candidate.Prefix) -c `
            "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" `
            *> $null
        if ($LASTEXITCODE -eq 0) {
            return $candidate
        }
    }

    throw "Python 3.11 or newer was not found. Install 64-bit Python, then rerun this script."
}

Write-Host "Alice OS setup"
Write-Host "Project: $projectRoot"

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    $python = Find-CompatiblePython
    Write-Host "Creating .venv with $($python.Label)..."
    & $python.Executable @($python.Prefix) -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Python could not create the virtual environment."
    }
}
else {
    Write-Host "Reusing existing .venv."
}

Write-Host "Updating packaging tools..."
& $venvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw "Could not update packaging tools. Check the network connection and pip configuration."
}

$installTarget = $projectRoot
if (-not $WithoutDev) {
    $installTarget = "${projectRoot}[dev]"
}

Write-Host "Installing Alice OS in editable mode..."
& $venvPython -m pip install --editable $installTarget
if ($LASTEXITCODE -ne 0) {
    throw "Alice OS dependency installation failed."
}

& $venvPython -c "import alice_os; print('Alice OS package import: OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Alice OS installed, but its package could not be imported."
}

$ollama = Get-Command "ollama" -ErrorAction SilentlyContinue
if ($ollama) {
    Write-Host "Ollama executable: $($ollama.Source)"
    try {
        $version = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 2
        Write-Host "Ollama service: running ($($version.version))"
    }
    catch {
        Write-Warning "Ollama is installed but its local service is not responding. Start the Ollama app (Windows) or run 'ollama serve'."
    }
}
else {
    Write-Warning "Ollama was not found. Alice can still use an HTTPS OpenAI-compatible provider, but local model pull/GGUF import needs Ollama."
}

Write-Host ""
Write-Host "Setup complete. Start Alice with:"
Write-Host "  .\scripts\start.cmd"
Write-Host ""
Write-Host "No model is downloaded automatically. See README.md for Ollama first-run steps."
