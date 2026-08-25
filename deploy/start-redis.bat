@echo off
title Vue3Sys - Redis
REM 自动定位到项目根目录\Redis（支持任意盘符，不依赖硬编码 D:\vue3sys）
set "REDIS_DIR=%~dp0..\Redis"
cd /d "%REDIS_DIR%"
if not exist redis-server.exe (
    echo [ERROR] redis-server.exe not found at: %REDIS_DIR%
    echo Please ensure the Redis folder is placed alongside deploy\, youlai-django\, vue3-element-admin\
    pause
    exit /b 1
)
echo Redis directory: %REDIS_DIR%
if exist redis.windows.conf (
    echo Using config: redis.windows.conf
    redis-server.exe redis.windows.conf
) else (
    echo WARNING: redis.windows.conf not found, starting with defaults (no password)
    redis-server.exe
)
