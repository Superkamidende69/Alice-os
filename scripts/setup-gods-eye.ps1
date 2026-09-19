[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$toolsDir = Join-Path $project 'tools'
$checkout = Join-Path $toolsDir 'gods-eye-view'
$revision = 'a65d9d85f1faa06ae7df235d7fa8a29b026b7a5b'
New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
if (-not (Test-Path (Join-Path $checkout '.git'))) {
    if (Test-Path $checkout) { throw 'The God''s Eye directory exists but is not a Git checkout.' }
    git clone --no-checkout https://github.com/bilawalsidhu/gods-eye-view.git $checkout
    if ($LASTEXITCODE -ne 0) { throw 'Could not clone God''s Eye View.' }
    git -C $checkout checkout --detach $revision
    if ($LASTEXITCODE -ne 0) { throw 'Could not check out the pinned revision.' }
}
$current = (git -C $checkout rev-parse HEAD).Trim()
if ($current -ne $revision) { throw 'Existing checkout differs from the tested revision. Preserve your changes and use a separate checkout.' }
if (git -C $checkout status --porcelain --untracked-files=no) { throw 'Upstream source has local edits. Preserve them before reinstalling.' }
# A private, pinned Node runtime keeps setup independent of the system PATH.
$nodeName = 'node-v24.14.0-win-x64'
$nodeRoot = Join-Path $toolsDir $nodeName
if (-not (Test-Path (Join-Path $nodeRoot 'node.exe'))) {
    $archive = Join-Path $toolsDir "$nodeName.zip"
    $base = 'https://nodejs.org/dist/v24.14.0'
    $checksums = (Invoke-WebRequest "$base/SHASUMS256.txt").Content
    $line = ($checksums -split "`n" | Where-Object { $_ -match "\s+$([regex]::Escape($nodeName)).zip\s*$" })
    if (-not $line) { throw 'Official Node checksum was not found.' }
    Invoke-WebRequest "$base/$nodeName.zip" -OutFile $archive
    $expected = ($line.Trim() -split '\s+')[0]
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'Node archive checksum mismatch.' }
    Expand-Archive -LiteralPath $archive -DestinationPath $toolsDir
    Remove-Item -LiteralPath $archive
}
$oldPath = $env:PATH
try {
    $env:PATH = "$nodeRoot;$oldPath"
    Push-Location $checkout
    try {
        & (Join-Path $nodeRoot 'node.exe') (Join-Path $nodeRoot 'node_modules/npm/bin/npm-cli.js') ci --ignore-scripts --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
        & (Join-Path $nodeRoot 'node.exe') scripts/setup-doctor.mjs
        if ($LASTEXITCODE -ne 0) { throw 'God''s Eye setup checks failed.' }
    } finally { Pop-Location }
} finally { $env:PATH = $oldPath }
Write-Host 'God''s Eye View is ready. Restart Alice, open World View, and click Start globe.'
