# Import MySQL database (ASCII-only)

param(
    [string]$SqlFile = '',
    [switch]$CreateDatabase,
    [switch]$AutoImport,
    [switch]$SkipMigrate
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
        throw "Create database failed. Check DB_USER / DB_PASSWORD in .env"
    }
    Write-Ok "Database ready"
} elseif (-not $AutoImport) {
    # Optionally confirm drop+recreate when DB already has tables
    $tables = & mysql -h $dbHost -P $dbPort -u $dbUser "-p$dbPass" -N -e "USE ``$dbName``; SHOW TABLES;" 2>&1
    if ($LASTEXITCODE -eq 0 -and $tables) {
        Write-Warn "Database $dbName already has $($tables.Count) tables"
        $drop = Read-Host "Drop and recreate database before import? (y/N)"
        if ($drop -eq 'y' -or $drop -eq 'Y') {
            & mysql -h $dbHost -P $dbPort -u $dbUser "-p$dbPass" -e "DROP DATABASE ``$dbName``; CREATE DATABASE ``$dbName`` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
            if ($LASTEXITCODE -ne 0) { throw "Recreate database failed" }
            Write-Ok "Database recreated clean"
        }
    }
}

Write-Host "Importing (may take several minutes)..."
$cmd = "mysql -h $dbHost -P $dbPort -u $dbUser -p$dbPass $dbName --default-character-set=utf8mb4 < `"$SqlFile`""
cmd /c $cmd
if ($LASTEXITCODE -ne 0) {
    throw "SQL import failed. Check MySQL password and service"
}
Write-Ok "Database imported"

# After import: run migrate to reconcile schema + apply any new migrations, and collect static
if (-not $SkipMigrate -and (Test-Path $paths.VenvPython)) {
    Write-Step "Post-import: Django migrate --fake-initial then migrate"
    Push-Location $paths.BackendRoot
    # --fake-initial so Django doesn't try to apply already-existing create-table migrations
    & $paths.VenvPython manage.py migrate --fake-initial --noinput 2>&1 | Out-Host
    & $paths.VenvPython manage.py migrate --noinput 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "migrate reported non-zero exit; see output above"
    } else {
        Write-Ok "migrate OK (synced with imported schema)"
    }
    Pop-Location

    Write-Step "Post-import: collectstatic (for admin / static assets via Nginx)"
    Push-Location $paths.BackendRoot
    & $paths.VenvPython manage.py collectstatic --noinput 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "collectstatic failed (non-critical for dev, needed for Nginx static)"
    } else {
        Write-Ok "collectstatic OK"
    }
    Pop-Location
}

Write-Ok "Import done. Next: start-all.ps1"
