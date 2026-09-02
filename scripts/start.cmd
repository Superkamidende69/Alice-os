@echo off
setlocal

where pwsh.exe >nul 2>nul
if not errorlevel 1 goto use_pwsh

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
exit /b %errorlevel%

:use_pwsh
pwsh.exe -NoLogo -NoProfile -File "%~dp0start.ps1" %*
exit /b %errorlevel%
