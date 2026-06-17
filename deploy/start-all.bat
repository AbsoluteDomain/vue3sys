@echo off
title Vue3Sys - Start All

cd /d "%~dp0"
echo.
echo Start order: Redis -^> Django -^> Frontend
echo Three CMD windows will open. Close window to stop service.
echo.

start "Vue3Sys-Redis" cmd /k "%~dp0start-redis.bat"
timeout /t 2 /nobreak >nul

start "Vue3Sys-Django" cmd /k "%~dp0start-backend.bat"
timeout /t 3 /nobreak >nul

start "Vue3Sys-Frontend" cmd /k "%~dp0start-frontend.bat"

echo.
echo Open browser: http://localhost:3000
echo API: http://localhost:8000
echo.
pause
