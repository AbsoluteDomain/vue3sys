@echo off
title Vue3Sys - Frontend
REM 自动定位前端目录：deploy 目录的上一级\vue3-element-admin
set "FRONTEND_DIR=%~dp0..\vue3-element-admin"
cd /d "%FRONTEND_DIR%"

where pnpm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pnpm not found. Please run: npm install -g pnpm
    echo (and ensure Node.js is installed first)
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo node_modules not found. Running pnpm install...
    pnpm install
    if errorlevel 1 (
        echo [ERROR] pnpm install failed
        pause
        exit /b 1
    )
)

echo Frontend directory: %FRONTEND_DIR%
echo Starting frontend http://localhost:3000 (Ctrl+C to stop)
pnpm run dev
pause
