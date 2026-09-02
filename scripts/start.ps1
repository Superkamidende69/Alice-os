[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 7788,

    [switch]$NoBrowser,

    [switch]$NoLlama
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$envFile = Join-Path $projectRoot ".env"

function Import-AliceEnvFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    foreach ($rawLine in Get-Content -LiteralPath $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }
        if ($line -notmatch '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            throw "Invalid .env entry. Use KEY=VALUE syntax: $rawLine"
        }
        $name = $Matches[1]
        $value = $Matches[2].Trim()
        if ($value.Length -ge 2) {
            $first = $value.Substring(0, 1)
            $last = $value.Substring($value.Length - 1, 1)
            if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

function Start-AliceLlamaProvider {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$DataDirectory
    )

    $existing = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "llama.cpp provider is already running at http://127.0.0.1:8080"
        return
    }

    $llamaServer = Join-Path $ProjectRoot "tools\llama.cpp\bin3\llama-server.exe"
    $model = Join-Path $DataDirectory "models\huggingface\empero-ai--Qwen3.8-2B-Distill-GGUF\Qwen3.8-2B-Q4_K_M.gguf"
    if (-not (Test-Path -LiteralPath $llamaServer -PathType Leaf) -or -not (Test-Path -LiteralPath $model -PathType Leaf)) {
        Write-Warning "llama.cpp or the Qwen Q4 model is missing, so Alice will start without its bundled provider."
        return
    }

    $logDirectory = Join-Path $DataDirectory "logs"
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $stdout = Join-Path $logDirectory "llama-$stamp.log"
    $stderr = Join-Path $logDirectory "llama-$stamp.err.log"
    $llamaArguments = @(
        "-m", $model, "-ngl", "99", "-c", "3072", "-np", "1", "-t", "6", "-tb", "8",
        "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0", "--sleep-idle-seconds", "300",
        "--host", "127.0.0.1", "--port", "8080"
    )
    Start-Process -FilePath $llamaServer -ArgumentList $llamaArguments -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
    Write-Host "Starting bundled llama.cpp provider at http://127.0.0.1:8080"
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    throw "Alice's virtual environment is missing. Run .\scripts\setup.ps1 first."
}

if (Test-Path -LiteralPath $envFile -PathType Leaf) {
    Import-AliceEnvFile -Path $envFile
}

if ([string]::IsNullOrWhiteSpace($env:ALICE_HOME)) {
    $env:ALICE_HOME = Join-Path $projectRoot ".alice-data"
}

if (-not $NoLlama) {
    Start-AliceLlamaProvider -ProjectRoot $projectRoot -DataDirectory $env:ALICE_HOME
}

$aliceArguments = @("-m", "alice_os", "--port", $Port.ToString())
if ($NoBrowser) {
    $aliceArguments += "--no-browser"
}

Write-Host "Starting Alice OS at http://127.0.0.1:$Port"
Write-Host "Data directory: $env:ALICE_HOME"

$exitCode = 0
Push-Location $projectRoot
try {
    & $venvPython @aliceArguments
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $exitCode
