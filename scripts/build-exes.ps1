[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Run scripts\setup.ps1 -Minimal first." }
& $python -m pip install --upgrade pyinstaller
& $python -m PyInstaller --noconfirm --clean --onedir --name AliceOS `
  --add-data "$root\web;web" --add-data "$root\scripts;scripts" `
  --additional-hooks-dir "$root\scripts\pyinstaller-hooks" `
  --paths "$root\src" "$root\src\aliceos_app.py"
& $python -m PyInstaller --noconfirm --clean --onefile --console --name AliceOS-Installer `
  --add-data "$root\scripts;scripts" --add-data "$root\dist\AliceOS;app" `
  --paths "$root\src" "$root\src\aliceos_installer.py"
Write-Host "Built dist\AliceOS\AliceOS.exe and dist\AliceOS-Installer.exe"
