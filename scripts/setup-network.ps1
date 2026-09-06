[CmdletBinding()]
param(
    [string]$Hostname = "aliceos.local"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Run Alice setup first." }
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw "Run this script in PowerShell as Administrator to add Alice's LAN firewall rules."
}

Push-Location $projectRoot
try {
    $detailsJson = & $python -m alice_os.network_setup --hostname $Hostname
    if ($LASTEXITCODE -ne 0) { throw "Alice certificate preparation failed." }
    $details = $detailsJson | ConvertFrom-Json
    $caPath = $details.ca_path
    $runtimePython = $details.runtime_python

    foreach ($rule in @(
        @{ Name = 'AliceOS-LAN-Web'; Protocol = 'TCP'; Ports = @('80', '443') },
        @{ Name = 'AliceOS-LAN-mDNS'; Protocol = 'UDP'; Ports = @('5353') }
    )) {
        $existing = Get-NetFirewallRule -Name $rule.Name -ErrorAction SilentlyContinue
        if ($existing) {
            $existing | Set-NetFirewallRule -Enabled True -Action Allow -Direction Inbound -Profile Any
            $existing | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol $rule.Protocol -LocalPort $rule.Ports
            $existing | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress LocalSubnet
            $existing | Get-NetFirewallApplicationFilter | Set-NetFirewallApplicationFilter -Program $runtimePython
        } else {
            New-NetFirewallRule -Name $rule.Name -DisplayName $rule.Name -Direction Inbound `
                -Action Allow -Enabled True -Profile Any -Protocol $rule.Protocol `
                -LocalPort $rule.Ports -RemoteAddress LocalSubnet -Program $runtimePython | Out-Null
        }
    }
    Import-Certificate -FilePath $caPath -CertStoreLocation Cert:\LocalMachine\Root | Out-Null
    Write-Host "Alice LAN firewall rules and host certificate trust are configured."
    Write-Host "Start Alice with scripts\start-network.cmd, then open https://$Hostname/"
    Write-Host "Trust this PUBLIC CA on each client device: $caPath"
    Write-Host "Firewall rules allow only this Python runtime from the local subnet, including on Public network profiles."
} finally {
    Pop-Location
}
