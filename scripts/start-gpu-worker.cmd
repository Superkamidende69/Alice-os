@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-gpu-worker.ps1" %*
exit /b %errorlevel%
