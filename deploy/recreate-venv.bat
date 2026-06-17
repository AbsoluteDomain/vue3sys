@echo off
title Vue3Sys - Recreate venv (run once after copy to new PC)

cd /d "%~dp0"
echo.
echo ========================================
echo   Recreate Python venv on THIS machine
echo   (venv cannot be copied from old PC)
echo ========================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0recreate-venv.ps1"
echo.
pause
