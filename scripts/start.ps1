[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 443,

    [switch]$NoBrowser,

    [switch]$Network,

    [switch]$Https,

    [string]$Hostname = "aliceos.local",

    [switch]$NoLocalAI,

    [switch]$UseLocalAI,

    [switch]$NoLlama
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($Network) { $Https = $true }
if (-not $PSBoundParameters.ContainsKey('Port')) {
    $Port = if ($Https) { 443 } else { 7788 }
}

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

    $existing = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "llama.cpp provider is already running at http://127.0.0.1:8081"
        return
    }

    $llamaServer = Join-Path $ProjectRoot "tools\llama.cpp\bin3\llama-server.exe"
    $model = Join-Path $DataDirectory "models\huggingface\empero-ai--Qwen3.8-2B-Distill-GGUF\Qwen3.8-2B-Q4_K_M.gguf"
    $managedModelRoot = Join-Path $DataDirectory "models\localai"
    if (Test-Path -LiteralPath $managedModelRoot -PathType Container) {
        $managedModel = Get-ChildItem -LiteralPath $managedModelRoot -Filter "*.gguf" -File -Recurse |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($managedModel) {
            $model = $managedModel.FullName
        }
    }
    $savedModel = Join-Path $DataDirectory "loaded-model.txt"
    if (Test-Path -LiteralPath $savedModel -PathType Leaf) {
        $selectedModel = (Get-Content -LiteralPath $savedModel -Raw).Trim()
        if (Test-Path -LiteralPath $selectedModel -PathType Leaf) { $model = $selectedModel }
    }
    if (-not (Test-Path -LiteralPath $llamaServer -PathType Leaf) -or -not (Test-Path -LiteralPath $model -PathType Leaf)) {
        Write-Warning "llama.cpp or an Alice-managed GGUF model is missing, so Alice will start without its bundled provider."
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
        "--host", "127.0.0.1", "--port", "8081"
    )
    $rpcJson = & $venvPython -m alice_os.distributed --startup
    if ($LASTEXITCODE -ne 0) { throw "Could not read distributed GPU settings." }
    $rpcStartup = $rpcJson | ConvertFrom-Json
    if ($rpcStartup.defer) {
        Write-Host "GPU workers are selected. Open Models in Alice to load the model after connecting the workers."
        return
    }
    $llamaArguments += @($rpcStartup.arguments)
    Start-Process -FilePath $llamaServer -ArgumentList $llamaArguments -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
    Write-Host "Starting bundled llama.cpp provider with $([System.IO.Path]::GetFileName($model)) at http://127.0.0.1:8081"
}

function Start-AliceLocalAIService {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$DataDirectory
    )

    try {
        $null = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/readyz" -TimeoutSec 2
        Write-Host "LocalAI service is already running at http://127.0.0.1:8080"
        return
    }
    catch {
        # Start the managed container below when LocalAI is not ready.
    }

    $localAi = Get-Command "local-ai" -ErrorAction SilentlyContinue
    if (-not $localAi) { $localAi = Get-Command "localai" -ErrorAction SilentlyContinue }
    $bundledLocalAi = Join-Path $ProjectRoot "tools\localai\local-ai.exe"
    $logDirectory = Join-Path $DataDirectory "logs"
    $modelDirectory = Join-Path $DataDirectory "models\localai"
    New-Item -ItemType Directory -Path $logDirectory, $modelDirectory -Force | Out-Null

    if ($localAi -or (Test-Path -LiteralPath $bundledLocalAi -PathType Leaf)) {
        $executable = if ($localAi) { $localAi.Source } else { $bundledLocalAi }
        $stdout = Join-Path $logDirectory "localai.log"
        $stderr = Join-Path $logDirectory "localai.err.log"
        Start-Process -FilePath $executable -ArgumentList @(
            "run", "--address", "127.0.0.1:8080", "--models-path", $modelDirectory
        ) -WorkingDirectory $DataDirectory -WindowStyle Hidden `
            -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
        Write-Host "Starting native LocalAI at http://127.0.0.1:8080"
    }
    else {
        $wsl = Get-Command "wsl.exe" -ErrorAction SilentlyContinue
        $distro = ""
        if ($wsl) {
            $rawDistros = ((& $wsl.Source -l -q 2>$null) -join "`n") -replace "`0", ""
            $distro = ($rawDistros -split "`r?`n" |
                ForEach-Object { $_.Trim() } |
                Where-Object { $_ -and $_ -notmatch "^docker-desktop(-data)?$" } |
                Select-Object -First 1)
        }
        if ($distro) {
            $linuxDataDirectory = ((& $wsl.Source -d $distro -- wslpath -a -u $DataDirectory 2>$null) -join "").Trim()
            if ($linuxDataDirectory) {
                $stdout = Join-Path $logDirectory "localai-wsl.log"
                $stderr = Join-Path $logDirectory "localai-wsl.err.log"
                Start-Process -FilePath $wsl.Source -ArgumentList @(
                    "-d", $distro, "--", "local-ai", "run", "--address", "127.0.0.1:8080",
                    "--models-path", "$linuxDataDirectory/models/localai"
                ) -WorkingDirectory $DataDirectory -WindowStyle Hidden `
                    -RedirectStandardOutput $stdout -RedirectStandardError $stderr | Out-Null
                Write-Host "Starting LocalAI from WSL distribution '$distro' at http://127.0.0.1:8080"
            }
        }
        else {
            $docker = Get-Command "docker" -ErrorAction SilentlyContinue
            if (-not $docker) {
                Write-Warning "LocalAI is not running. Install local-ai in WSL or place local-ai.exe under tools\localai."
                return
            }

            # Docker CLI can be installed while Docker Desktop is stopped. Keep
            # that normal state from terminating the Alice launcher.
            $dockerReady = $false
            try {
                & $docker.Source info *> $null
                $dockerReady = $LASTEXITCODE -eq 0
            }
            catch {
                $dockerReady = $false
            }
            if (-not $dockerReady) {
                Write-Warning "Docker is installed but its engine is not running; LocalAI was skipped. Start Docker Desktop or install LocalAI in WSL."
                return
            }

            $containerName = "alice-localai"
            $existing = (& $docker.Source ps -a --filter "name=^/$containerName$" --format "{{.Names}}" 2>$null)
            if ($existing -contains $containerName) {
                & $docker.Source start $containerName | Out-Null
            }
            else {
                $localDataDirectory = Join-Path $DataDirectory "localai-data"
                New-Item -ItemType Directory -Path $localDataDirectory -Force | Out-Null
                & $docker.Source run -d --name $containerName --restart unless-stopped `
                    -p "127.0.0.1:8080:8080" `
                    -v "${modelDirectory}:/models" `
                    -v "${localDataDirectory}:/data" `
                    "localai/localai:latest" | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    Write-Warning "LocalAI could not start. Run 'docker logs $containerName' to inspect it."
                    return
                }
            }
        }
    }

    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $null = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8080/readyz" -TimeoutSec 2
            Write-Host "Started LocalAI service at http://127.0.0.1:8080"
            return
        }
        catch {
            # LocalAI may need time to initialize or pull its backend.
        }
    }
    Write-Warning "LocalAI container started but did not become ready. Run 'docker logs $containerName'."
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    throw "Alice's virtual environment is missing. Run .\scripts\setup.ps1 first."
}

if (Test-Path -LiteralPath $envFile -PathType Leaf) {
    Import-AliceEnvFile -Path $envFile
}

& $venvPython -m alice_os --setup
if ($LASTEXITCODE -ne 0) { throw "Alice first-install setup failed." }
$env:ALICE_HOME = (& $venvPython -c "from alice_os.config import default_data_dir; print(default_data_dir())").Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not resolve Alice data directory." }
if ($Network) {
    $env:ALICE_NETWORK_MODE = "1"
    New-Item -ItemType Directory -Path $env:ALICE_HOME -Force | Out-Null
}

if ($UseLocalAI -and -not $NoLocalAI) {
    Start-AliceLocalAIService -ProjectRoot $projectRoot -DataDirectory $env:ALICE_HOME
}

if (-not $NoLlama) {
    Start-AliceLlamaProvider -ProjectRoot $projectRoot -DataDirectory $env:ALICE_HOME
}

$aliceArguments = @("-m", "alice_os", "--port", $Port.ToString())
if ($Network) {
    $aliceArguments += "--lan"
}
if ($Https) {
    $aliceArguments += "--https"
}
$aliceArguments += @("--hostname", $Hostname)
if ($NoBrowser) {
    $aliceArguments += "--no-browser"
}

if ($Network) {
    $lanAddress = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and
            $_.InterfaceAlias -notmatch "WSL|vEthernet|Default Switch|Loopback"
        } |
        Select-Object -First 1 -ExpandProperty IPAddress
    if ([string]::IsNullOrWhiteSpace($lanAddress)) { $lanAddress = "YOUR-LAN-IP" }
    Write-Host "Starting Alice OS for LAN access"
    $scheme = if ($Https) { "https" } else { "http" }
    $connectHost = if ($Https -and $Hostname) { $Hostname } else { $lanAddress }
    $portSuffix = if (($Https -and $Port -eq 443) -or (-not $Https -and $Port -eq 80)) { "" } else { ":$Port" }
    Write-Host "Connect at: $scheme`://$connectHost$portSuffix/ (then sign in)"
} else {
    Write-Host "Starting Alice OS; the server will print its connection address below."
}
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
