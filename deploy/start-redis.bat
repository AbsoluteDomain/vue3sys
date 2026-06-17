@echo off
title Vue3Sys - Redis
cd /d "D:\vue3sys\Redis"
if not exist redis-server.exe (
    echo redis-server.exe not found
    pause
    exit /b 1
)
if exist redis.windows.conf (
    redis-server.exe redis.windows.conf
) else (
    redis-server.exe
)
