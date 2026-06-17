@echo off
title vue3sys Deploy Menu

cd /d "%~dp0"
echo.
echo ========================================
echo   vue3sys Deploy - D:\vue3sys\deploy
echo ========================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
echo.
pause
