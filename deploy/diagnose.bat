@echo off
chcp 65001 >nul
title vue3sys deploy diagnose (ASCII)

cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0diagnose.ps1"
echo.
pause
