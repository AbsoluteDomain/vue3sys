# Generate backend and frontend .env files (ASCII-only)

param(
    [switch]$Force,
    [switch]$UseDefaults,
    [switch]$NoRedisAuth
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths
$templatePath = Join-Path $paths.DeployRoot 'templates\backend.env.template'
$feTemplatePath = Join-Path $paths.DeployRoot 'templates\frontend.env.development.template'

Write-Step "Generate config files"

if ((Test-Path $paths.BackendEnv) -and -not $Force -and -not $UseDefaults) {
    $overwrite = Read-Host "Backend .env exists. Overwrite? (y/N)"
    if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
        Write-Warn "Skip backend .env"
        $skipBackend = $true
    } else {
        $Force = $true
    }
}

if (-not $skipBackend -and ($Force -or $UseDefaults -or -not (Test-Path $paths.BackendEnv))) {
    if (-not (Test-Path $templatePath)) {
        throw "Template not found: $templatePath"
    }

    if ($UseDefaults) {
        Write-Host ""
        Write-Host "[AUTO] UseDefaults: filling .env with standard defaults (no prompts)" -ForegroundColor Cyan
        $dbHost = 'localhost'
        $dbPort = '3306'
        $dbName = 'youlai_admin_django'
        $dbUser = 'root'
        $dbPass = 'root'
        $redisHost = 'localhost'
        $redisPort = '6379'
        if ($NoRedisAuth) {
            $redisPass = ''
        } else {
            $redisPass = '123456'
        }
        $redisDb = '12'
        $minioHost = 'http://localhost:9000'
    } else {
        Write-Host ""
        Write-Host "Enter DB and Redis settings (Enter = default)" -ForegroundColor Yellow
        Write-Host "MySQL root password = password set during MySQL install" -ForegroundColor DarkGray

        $dbHost = Read-EnvValue 'DB_HOST' 'localhost'
        $dbPort = Read-EnvValue 'DB_PORT' '3306'
        $dbName = Read-EnvValue 'DB_NAME' 'youlai_admin_django'
        $dbUser = Read-EnvValue 'DB_USER' 'root'
        $dbPass = Read-EnvValue 'DB_PASSWORD' 'root'

        $redisHost = Read-EnvValue 'REDIS_HOST' 'localhost'
        $redisPort = Read-EnvValue 'REDIS_PORT' '6379'
        $redisPass = Read-EnvValue 'REDIS_PASSWORD' '123456'
        $redisDb = Read-EnvValue 'REDIS_DB' '12'

        $minioHost = Read-EnvValue 'MINIO_HOST_PORT' 'http://localhost:9000'
    }

    $content = Get-Content $templatePath -Raw -Encoding UTF8
    $content = $content -replace '\{\{DB_HOST\}\}', $dbHost
    $content = $content -replace '\{\{DB_PORT\}\}', $dbPort
    $content = $content -replace '\{\{DB_NAME\}\}', $dbName
    $content = $content -replace '\{\{DB_USER\}\}', $dbUser
    $content = $content -replace '\{\{DB_PASSWORD\}\}', $dbPass
    $content = $content -replace '\{\{REDIS_HOST\}\}', $redisHost
    $content = $content -replace '\{\{REDIS_PORT\}\}', $redisPort
    $content = $content -replace '\{\{REDIS_PASSWORD\}\}', $redisPass
    $content = $content -replace '\{\{REDIS_DB\}\}', $redisDb
    $content = $content -replace '\{\{MINIO_HOST_PORT\}\}', $minioHost

    $djangoSecret = New-RandomSecret -Length 50
    $jwtSecret = New-RandomSecret -Length 64
    $content = $content -replace 'CHANGE_ME_GENERATE_A_RANDOM_SECRET_KEY', $djangoSecret
    $content = $content -replace 'CHANGE_ME_JWT_SECRET_AT_LEAST_64_CHARS', $jwtSecret

    [System.IO.File]::WriteAllText($paths.BackendEnv, $content, [System.Text.UTF8Encoding]::new($false))
    Write-Ok "Created: $($paths.BackendEnv)"
}

$feEnvPath = Join-Path $paths.FrontendRoot '.env.development'
if ((Test-Path $feEnvPath) -and -not $Force -and -not $UseDefaults) {
    Write-Warn "Frontend .env.development exists, not overwritten"
} elseif (Test-Path $feTemplatePath) {
    Copy-Item $feTemplatePath $feEnvPath -Force
    Write-Ok "Created: $feEnvPath"
}

# Ensure frontend .env.production exists (for production build / Nginx deploy)
$feProdEnvPath = Join-Path $paths.FrontendRoot '.env.production'
$feProdTplPath = Join-Path $paths.DeployRoot 'templates\frontend.env.production.template'
if (-not (Test-Path $feProdEnvPath) -and (Test-Path $feProdTplPath)) {
    Copy-Item $feProdTplPath $feProdEnvPath -Force
    Write-Ok "Created: $feProdEnvPath"
}

Write-Step "Sync Redis password to redis.windows.conf"
$redisConf = Join-Path $paths.RedisRoot 'redis.windows.conf'
if (Test-Path $redisConf) {
    $envLines = Get-Content $paths.BackendEnv -Encoding UTF8 | Where-Object { $_ -match '^REDIS_PASSWORD=' }
    if ($envLines) {
        $redisPass = ($envLines[0] -replace '^REDIS_PASSWORD=', '').Trim()
        $conf = Get-Content $redisConf -Encoding UTF8
        $hasRequirePass = $false
        $newConf = @()
        foreach ($line in $conf) {
            if ($line -match '^\s*requirepass\s') {
                if ([string]::IsNullOrWhiteSpace($redisPass)) {
                    # comment out requirepass when no password
                    $newConf += "# requirepass disabled (empty REDIS_PASSWORD)"
                } else {
                    $newConf += "requirepass $redisPass"
                }
                $hasRequirePass = $true
            } else {
                $newConf += $line
            }
        }
        if (-not $hasRequirePass -and -not [string]::IsNullOrWhiteSpace($redisPass)) {
            $newConf += "requirepass $redisPass"
        }
        [System.IO.File]::WriteAllLines($redisConf, $newConf, [System.Text.UTF8Encoding]::new($false))
        if ([string]::IsNullOrWhiteSpace($redisPass)) {
            Write-Ok "redis.windows.conf: no requirepass (auth disabled, matches empty REDIS_PASSWORD)"
        } else {
            Write-Ok "Updated redis.windows.conf password"
        }
    }
} else {
    Write-Warn "redis.windows.conf not found"
}

Write-Ok "Done. Next: install-deps.ps1"
