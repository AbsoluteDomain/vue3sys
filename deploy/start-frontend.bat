@echo off
title Vue3Sys - Frontend
cd /d "D:\vue3sys\vue3-element-admin"

where pnpm >nul 2>&1
if errorlevel 1 (
    echo pnpm not found. Run: npm install -g pnpm
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo node_modules not found. Run: pnpm install
    echo Or run deploy menu option 4 install-deps.ps1
    pause
    exit /b 1
)

echo Starting frontend http://localhost:3000
pnpm run dev
pause
