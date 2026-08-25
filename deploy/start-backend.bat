@echo off
title Vue3Sys - Django Backend
REM 自动定位后端目录：deploy 目录的上一级\youlai-django
set "BACKEND_DIR=%~dp0..\youlai-django"
cd /d "%BACKEND_DIR%"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] venv not found at %BACKEND_DIR%\venv
    echo Please run deploy\recreate-venv.bat or deploy\install-deps.ps1 first
    pause
    exit /b 1
)

if not exist ".env" (
    echo [ERROR] .env not found at %BACKEND_DIR%\.env
    echo Please run deploy menu option 3 (configure.ps1) first
    pause
    exit /b 1
)

echo Django directory: %BACKEND_DIR%
echo Starting Django http://localhost:8000 (Ctrl+C to stop)
venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
pause
