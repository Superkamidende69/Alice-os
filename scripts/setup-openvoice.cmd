@echo off
setlocal

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-openvoice.ps1" %*
exit /b %errorlevel%
