[CmdletBinding()]
param(
    [ValidateRange(1024,65535)][int]$Port = 50052,
    [ValidatePattern('^[A-Za-z0-9_,.-]+$')][string]$Device = 'CUDA0'
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$rpc = Join-Path $projectRoot 'tools\llama.cpp\bin3\ggml-rpc-server.exe'
if (-not (Test-Path -LiteralPath $rpc)) { throw 'Install a matching llama.cpp build with RPC support first.' }
Write-Host "Experimental GPU worker on 127.0.0.1:$Port. Connect through an authenticated SSH tunnel."
Write-Host 'Keep this terminal running. Press Ctrl+C to stop. No raw LAN listener is opened.'
& $rpc --host 127.0.0.1 --port $Port --device $Device
exit $LASTEXITCODE
