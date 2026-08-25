@echo off
chcp 65001 >nul
title vue3sys Deploy Menu

cd /d "%~dp0"
REM 动态显示当前路径，而不是硬编码 D:\vue3sys
set "PROJECT_ROOT=%~dp0.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"

echo.
echo ========================================
echo   vue3sys Deploy - %PROJECT_ROOT%\deploy
echo ========================================
echo.
echo Tip: 全自动无人值守部署（无需交互选菜单）请双击  "一键部署-全自动.bat"
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
echo.
pause
