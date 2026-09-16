[CmdletBinding()]
param(
    [switch]$WithoutDev,

    [switch]$Minimal,

    [switch]$SkipOpenVoice,

    [switch]$SkipLlama
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$venvRoot = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"

function Update-ProcessPath {
    # winget does not always update this already-running PowerShell process.
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = @($machinePath, $userPath, $env:Path | Where-Object { $_ }) -join ";"
}

function Install-WingetPackage {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $winget = Get-Command "winget.exe" -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "$Name is required for the full installer, but Windows App Installer (winget) was not found. Install App Installer from Microsoft Store, then rerun setup."
    }
    Write-Host "Installing $Name..."
    & $winget.Source install --id $Id --exact --source winget --scope user --disable-interactivity `
        --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install $Name with winget (exit code $LASTEXITCODE)."
    }
    Update-ProcessPath
}

function Install-LlamaCppBackend {
    $binaryDirectory = Join-Path $projectRoot "tools\llama.cpp\bin3"
    $server = Join-Path $binaryDirectory "llama-server.exe"
    if (Test-Path -LiteralPath $server -PathType Leaf) {
        Write-Host "Bundled llama.cpp backend: $server"
        return
    }

    Write-Host "Downloading the llama.cpp local model backend..."
    try {
        $release = Invoke-RestMethod -Uri "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest" `
            -Headers @{ "User-Agent" = "Alice-OS-Setup" }
        $assets = @($release.assets)
        $hasNvidia = [bool](Get-Command "nvidia-smi.exe" -ErrorAction SilentlyContinue)
        $asset = $null
        if ($hasNvidia) {
            $asset = $assets | Where-Object { $_.name -match "^llama-.*win-cuda.*-x64\.zip$" } |
                Select-Object -First 1
        }
        if (-not $asset) {
            $asset = $assets | Where-Object { $_.name -match "^llama-.*win-avx2-x64\.zip$" } |
                Select-Object -First 1
        }
        if (-not $asset) {
            throw "No compatible Windows llama.cpp release asset was found."
        }
        $temporary = Join-Path ([System.IO.Path]::GetTempPath()) ("alice-llama-" + [guid]::NewGuid())
        $archive = Join-Path $temporary "llama.zip"
        $expanded = Join-Path $temporary "expanded"
        New-Item -ItemType Directory -Path $expanded -Force | Out-Null
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $asset.browser_download_url -OutFile $archive
            Expand-Archive -LiteralPath $archive -DestinationPath $expanded -Force
            $downloadedServer = Get-ChildItem -LiteralPath $expanded -Filter "llama-server.exe" -File -Recurse |
                Select-Object -First 1
            if (-not $downloadedServer) { throw "The downloaded llama.cpp archive did not contain llama-server.exe." }
            New-Item -ItemType Directory -Path $binaryDirectory -Force | Out-Null
            Copy-Item -Path (Join-Path $downloadedServer.Directory.FullName "*") -Destination $binaryDirectory -Recurse -Force
        }
        finally {
            if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
        }
    }
    catch {
        throw "Could not install the llama.cpp backend: $($_.Exception.Message)"
    }
    if (-not (Test-Path -LiteralPath $server -PathType Leaf)) {
        throw "llama.cpp installation completed without llama-server.exe."
    }
    Write-Host "llama.cpp backend installed: $server"
}

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

    if ($Minimal) {
        throw "Python 3.11 or newer was not found. Install 64-bit Python, then rerun this script."
    }
    Install-WingetPackage -Id "Python.Python.3.13" -Name "Python 3.13"
    foreach ($candidate in @(
        (Join-Path $env:LocalAppData "Programs\Python\Python313\python.exe"),
        "C:\Program Files\Python313\python.exe"
    )) {
        if ((Test-Path -LiteralPath $candidate -PathType Leaf) -and
            ((& $candidate -c "import sys; print(sys.version_info >= (3, 11))") -eq "True")) {
            return [pscustomobject]@{ Executable = $candidate; Prefix = @(); Label = "Python 3.13" }
        }
    }
    throw "Python was installed but could not be found. Close PowerShell, open it again, and rerun setup."
}

if ($Minimal) {
    $SkipOpenVoice = $true
    $SkipLlama = $true
}

Write-Host "Alice OS full setup"
Write-Host "Project: $projectRoot"
if (-not $Minimal) {
    Write-Host "This installs Alice, llama.cpp, OpenVoice, voice checkpoints, and their required runtimes."
}

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

& $venvPython -m alice_os --setup
if ($LASTEXITCODE -ne 0) { throw "Alice first-install setup failed." }

if (-not $SkipLlama) {
    Install-LlamaCppBackend
}

if (-not $SkipOpenVoice) {
    Write-Host "Preparing the OpenVoice speech backend and checkpoints. This can take several minutes."
    & (Join-Path $PSScriptRoot "setup-openvoice.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "OpenVoice setup failed. Rerun .\scripts\setup-openvoice.cmd after resolving the reported issue."
    }
}

Write-Host ""
Write-Host "Full setup complete. Start Alice with:"
Write-Host "  .\scripts\start.cmd"
Write-Host ""
Write-Host "No language model is downloaded automatically. Open Models in Alice to choose one."
if ($Minimal) { Write-Host "Minimal setup skipped llama.cpp and OpenVoice." }
