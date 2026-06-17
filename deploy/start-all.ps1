# Start Redis, Django, frontend (ASCII-only)

param(
    [switch]$SkipFrontend,
    [switch]$SkipRedis
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths

if (-not (Test-Path $paths.BackendEnv)) {
    throw "Run configure.ps1 first"
}
if (-not (Test-Path $paths.VenvPython)) {
    throw "Run install-deps.ps1 first"
}

Initialize-LogDir $paths.LogDir

function Start-InNewWindow {
    param(
        [string]$Title,
        [string]$WorkDir,
        [string]$Command
    )
    $cmdLine = "cd /d `"$WorkDir`" && $Command"
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/k', "title $Title && $cmdLine" -WorkingDirectory $WorkDir
    Write-Ok "Started: $Title"
}

Write-Step "Start services (close CMD window to stop)"

if (-not $SkipRedis) {
    $redisExe = Join-Path $paths.RedisRoot 'redis-server.exe'
    $redisConf = Join-Path $paths.RedisRoot 'redis.windows.conf'
    if (Test-Path $redisExe) {
        if (Test-Path $redisConf) {
            Start-InNewWindow -Title 'Vue3Sys-Redis' -WorkDir $paths.RedisRoot -Command "redis-server.exe redis.windows.conf"
        } else {
            Start-InNewWindow -Title 'Vue3Sys-Redis' -WorkDir $paths.RedisRoot -Command "redis-server.exe"
        }
        Start-Sleep -Seconds 2
    } else {
        Write-Warn "Redis\redis-server.exe not found"
    }
}

$djangoCmd = "`"$($paths.VenvPython)`" manage.py runserver 0.0.0.0:8000"
Start-InNewWindow -Title 'Vue3Sys-Django' -WorkDir $paths.BackendRoot -Command $djangoCmd

if (-not $SkipFrontend) {
    if (-not (Test-CommandExists 'pnpm')) {
        Write-Warn "pnpm not found, skip frontend"
    } else {
        Start-Sleep -Seconds 2
        Start-InNewWindow -Title 'Vue3Sys-Frontend' -WorkDir $paths.FrontendRoot -Command "pnpm run dev"
    }
}

Write-Host ""
Write-Ok "Services started"
Write-Host "  API  : http://localhost:8000" -ForegroundColor Gray
Write-Host "  Web  : http://localhost:3000" -ForegroundColor Gray
