@echo off
title Vue3Sys - Django Backend
cd /d "D:\vue3sys\youlai-django"

if not exist "venv\Scripts\python.exe" (
    echo venv not found. Run D:\vue3sys\deploy\recreate-venv.bat first
    pause
    exit /b 1
)

if not exist ".env" (
    echo .env not found. Run deploy menu option 3 configure.ps1 first
    pause
    exit /b 1
)

echo Starting Django http://localhost:8000
venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
pause
