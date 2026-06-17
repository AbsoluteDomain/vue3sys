@echo off
title vue3sys install prerequisites (Administrator)

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator...
    powershell.exe -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
echo Install Python Node MySQL pnpm - run as Administrator
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-prerequisites.ps1" -InstallAll
echo.
echo Check deploy\logs if failed
pause
