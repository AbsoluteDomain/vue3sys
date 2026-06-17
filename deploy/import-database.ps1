# Import MySQL database (ASCII-only)

param(
    [string]$SqlFile = '',
    [switch]$CreateDatabase
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths

if (-not (Test-Path $paths.BackendEnv)) {
    throw "Run configure.ps1 first"
}

function Get-EnvVar {
    param([string]$Key)
    $line = Get-Content $paths.BackendEnv -Encoding UTF8 | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
    if (-not $line) { return '' }
    return ($line -replace "^$Key=", '').Trim()
}

$dbHost = Get-EnvVar 'DB_HOST'
$dbPort = Get-EnvVar 'DB_PORT'
$dbName = Get-EnvVar 'DB_NAME'
$dbUser = Get-EnvVar 'DB_USER'
$dbPass = Get-EnvVar 'DB_PASSWORD'

if (-not $SqlFile) {
    $SqlFile = Join-Path $paths.ProjectRoot 'youlai_admin_django.sql'
}

if (-not (Test-Path $SqlFile)) {
    throw "SQL file not found: $SqlFile"
}

if (-not (Test-CommandExists 'mysql')) {
    throw "mysql command not found. Add MySQL bin to PATH"
}

Write-Step "Import database"
Write-Host "Target: ${dbUser}@${dbHost}:${dbPort}/${dbName}"
Write-Host "File: $SqlFile"

if ($CreateDatabase) {
    Write-Host "Creating database $dbName ..."
    $createSql = "CREATE DATABASE IF NOT EXISTS ``$dbName`` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
    & mysql -h $dbHost -P $dbPort -u $dbUser "-p$dbPass" -e $createSql
    if ($LASTEXITCODE -ne 0) {
        throw "Create database failed"
    }
    Write-Ok "Database ready"
}

Write-Host "Importing (may take several minutes)..."
$cmd = "mysql -h $dbHost -P $dbPort -u $dbUser -p$dbPass $dbName --default-character-set=utf8mb4 < `"$SqlFile`""
cmd /c $cmd
if ($LASTEXITCODE -ne 0) {
    throw "SQL import failed. Check MySQL password and service"
}

Write-Ok "Import done. Next: start-all.ps1"
