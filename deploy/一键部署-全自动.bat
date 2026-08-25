@echo off
chcp 65001 >nul
title vue3sys UNATTENDED One-Click Deploy

REM =====================================================
REM  客户机一键部署（全程无需手动输入）
REM  推荐：右键 -> 以管理员身份运行 （否则无法自动安装 Python/Node/MySQL）
REM  部署顺序：安装前置环境 -> 生成默认配置 -> 安装依赖 -> 建库导入SQL -> 迁移+静态 -> 启动Redis/Django/前端
REM =====================================================

REM 管理员检测：非管理员时尝试自动提权
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [提示] 需要以管理员身份运行才能自动安装 Python/Node/MySQL。
    echo 正在请求管理员权限...
    powershell.exe -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
REM 显示实际路径
set "PROJECT_ROOT=%~dp0.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"

echo.
echo ========================================
echo   vue3sys UNATTENDED One-Click Deploy
echo   Project root: %PROJECT_ROOT%
echo ========================================
echo.
echo [Info] Running as Administrator. Auto-installing prerequisites if needed.
echo        No prompts will appear. Wait for the final banner.
echo.

REM 调用 setup.ps1 -Action auto
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" -Action auto
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
    echo ========================================
    echo   Deployment SUCCESS
    echo   Web UI : http://localhost:3000
    echo   API    : http://localhost:8000
    echo ========================================
) else (
    echo ========================================
    echo   Deployment FAILED with code %EXITCODE%
    echo   Check logs in: %~dp0logs\
    echo   Common fixes:
    echo     1. Make sure you ran as Administrator
    echo     2. Check MySQL80 service is running
    echo     3. If MySQL password is not 'root', edit youlai-django\.env manually
    echo ========================================
)
echo.
pause
