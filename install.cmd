@echo off
setlocal EnableExtensions
title Alice OS Installer

echo.
echo ================================================================
echo                    Alice OS CLI Installer
echo ================================================================
echo.
echo This installer will prepare llama.cpp, OpenVoice, and Alice OS.
echo You will be prompted to choose Alice's data folder and create an
echo administrator username and password during the first installation.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1" %*
set "INSTALL_EXIT=%ERRORLEVEL%"

echo.
if not "%INSTALL_EXIT%"=="0" (
    echo Installation did not finish. Review the error above, then rerun this file.
) else (
    echo Installation finished successfully.
    echo Start Alice later with: scripts\start.cmd
)
echo.
pause
exit /b %INSTALL_EXIT%
