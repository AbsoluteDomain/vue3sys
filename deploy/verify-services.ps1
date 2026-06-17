# Verify MySQL Redis Django (ASCII-only)

$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths

function Get-EnvVar {
    param([string]$Key)
    if (-not (Test-Path $paths.BackendEnv)) { return '' }
    $line = Get-Content $paths.BackendEnv -Encoding UTF8 | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
    if (-not $line) { return '' }
    return ($line -replace "^$Key=", '').Trim()
}

Write-Step "Load config"
$dbHost = Get-EnvVar 'DB_HOST'
$dbPort = [int](Get-EnvVar 'DB_PORT')
if (-not $dbPort) { $dbPort = 3306 }
$dbName = Get-EnvVar 'DB_NAME'
$dbUser = Get-EnvVar 'DB_USER'
$dbPass = Get-EnvVar 'DB_PASSWORD'

$allOk = $true

Write-Step "MySQL"
if (Test-TcpPort -HostName $dbHost -Port $dbPort) {
    Write-Ok "MySQL port $dbPort open"
    if (Test-CommandExists 'mysql') {
        $env:MYSQL_PWD = $dbPass
        $result = & mysql -h $dbHost -P $dbPort -u $dbUser -e "USE ``$dbName``; SELECT 1;" 2>&1
        Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "MySQL login OK, db $dbName"
        } else {
            Write-Fail "MySQL login failed: $result"
            $allOk = $false
        }
    }
} else {
    Write-Fail "MySQL port $dbPort not open"
    $allOk = $false
}

Write-Step "Redis"
if (Test-TcpPort -Port 6379) {
    Write-Ok "Redis port 6379 open"
} else {
    Write-Fail "Redis not running"
    $allOk = $false
}

Write-Step "Django API"
if (Test-TcpPort -Port 8000) {
    try {
        $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/auth/captcha' -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200) {
            Write-Ok "Django API OK (HTTP 200)"
        } else {
            Write-Warn "Django HTTP $($resp.StatusCode)"
        }
    } catch {
        Write-Warn "Django port open but API failed: $($_.Exception.Message)"
    }
} else {
    Write-Fail "Django not running (port 8000)"
    $allOk = $false
}

Write-Step "Frontend"
if (Test-TcpPort -Port 3000) {
    Write-Ok "Frontend port 3000 open"
} else {
    Write-Warn "Frontend not running (optional)"
}

if ($allOk) {
    Write-Ok "Core services OK"
    exit 0
}
exit 1
