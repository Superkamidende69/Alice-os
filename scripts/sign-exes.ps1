[CmdletBinding()]
param(
    [string]$CertificatePath = "",
    [string]$CertificatePassword = "",
    [string]$CertificateThumbprint = "",
    [string]$TimestampUrl = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$targets = @(
    (Join-Path $root "dist\AliceOS-Installer.exe"),
    (Join-Path $root "dist\AliceOS\AliceOS.exe")
)
foreach ($target in $targets) {
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
        throw "Build the EXEs first. Missing: $target"
    }
}

$signTool = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
if (-not $signTool) {
    $kits = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Filter "signtool.exe" -Recurse -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($kits) { $signTool = [pscustomobject]@{ Source = $kits.FullName } }
}
if (-not $signTool) {
    throw "signtool.exe was not found. Install the Windows SDK Signing Tools, then rerun this script."
}

if ($CertificatePath) {
    if (-not (Test-Path -LiteralPath $CertificatePath -PathType Leaf)) {
        throw "Certificate file was not found: $CertificatePath"
    }
    $arguments = @("sign", "/fd", "SHA256", "/f", $CertificatePath)
    if ($CertificatePassword) { $arguments += @("/p", $CertificatePassword) }
}
elseif ($CertificateThumbprint) {
    $arguments = @("sign", "/fd", "SHA256", "/sha1", $CertificateThumbprint)
}
else {
    throw "Provide -CertificatePath for a PFX file or -CertificateThumbprint for a certificate installed in Windows."
}

if ($TimestampUrl) {
    $arguments += @("/tr", $TimestampUrl, "/td", "SHA256")
}
else {
    Write-Warning "No timestamp server was supplied. The signature will stop validating when the certificate expires."
}

foreach ($target in $targets) {
    Write-Host "Signing $target"
    & $signTool.Source @arguments $target
    if ($LASTEXITCODE -ne 0) { throw "Signing failed for $target (exit code $LASTEXITCODE)." }
    & $signTool.Source verify "/pa" "/v" $target
    if ($LASTEXITCODE -ne 0) { throw "Signature verification failed for $target (exit code $LASTEXITCODE)." }
}

Write-Host "Both Alice OS EXEs are signed and verified."
