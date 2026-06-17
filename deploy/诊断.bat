@echo off
title vue3sys diagnose

cd /d "%~dp0"
echo Running diagnose...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0diagnose.ps1"
echo.
pause
