#Requires -Version 5.0
<#
.SYNOPSIS
  Import database dump from server A into server B and upgrade schema.
.DESCRIPTION
  Run on server B. Steps:
    1. Pre-check: backup current B DB + compare table names (A dump vs B)
    2. Rebuild: DROP DATABASE + CREATE + import A dump
    3. Upgrade: git pull + python manage.py migrate (apply new migrations)
    4. Verify: showmigrations + key table row counts
  If anything goes wrong, restore from the backup file (command printed at the end).
.PARAMETER DumpFile
  Full SQL dump file exported from server A.
.PARAMETER ProjectDir
  youlai-django project directory on server B.
.PARAMETER DbName / DbUser / DbPass / DbHost / DbPort
  MySQL connection parameters for server B.
.EXAMPLE
  .\deploy\migrate-db-from-a.ps1
.EXAMPLE
  .\deploy\migrate-db-from-a.ps1 -WhatIf
#>
param(
    [string]$DumpFile = "D:\vue3sys\youlai_admin_django_29.sql",
    [string]$ProjectDir = "D:\vue3sys\youlai-django",
    [string]$DbName = "youlai_admin_django",
    [string]$DbUser = "znb",
    [string]$DbPass = "123456",
    [string]$DbHost = "localhost",
    [int]$DbPort = 3306,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n========== $msg ==========" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "[!]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[X]  $msg" -ForegroundColor Red }

# Pass MySQL password via env var to avoid command-line warning
$env:MYSQL_PWD = $DbPass
$mysqlArgs = @("-u$DbUser","-h$DbHost","-P$DbPort","--default-character-set=utf8mb4")

# ---------- Pre-check ----------
Write-Step "Pre-check"

if (-not (Test-Path $DumpFile)) {
    Write-Err "Dump file not found: $DumpFile"
    exit 1
}
$dumpSize = [math]::Round((Get-Item $DumpFile).Length / 1MB, 2)
Write-Ok "Dump file exists: $DumpFile ($dumpSize MB)"

foreach ($cmd in @("mysql","mysqldump","git")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Err "Command not found in PATH: $cmd"
        exit 1
    }
}
Write-Ok "mysql / mysqldump / git available"

if (-not (Test-Path "$ProjectDir\manage.py")) {
    Write-Err "Project dir invalid (manage.py not found): $ProjectDir"
    exit 1
}
Write-Ok "Project dir valid: $ProjectDir"

# Test MySQL connection
$testOut = & mysql @mysqlArgs $DbName -e "SELECT 1;" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "MySQL connection failed: $testOut"
    exit 1
}
Write-Ok "MySQL connection OK"

if ($WhatIf) {
    Write-Warn2 "-WhatIf set: will run pre-check only (no rebuild/import/upgrade)"
}

# ---------- Stage 1: backup + diff ----------
Write-Step "Stage 1: backup current B database (restore point)"

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "D:\vue3sys\backup_B_before_import_$ts.sql"
Write-Host "Backup to: $backupFile"
& mysqldump @mysqlArgs --single-transaction --routines --triggers $DbName | Out-File -Encoding UTF8 $backupFile
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $backupFile) -or (Get-Item $backupFile).Length -lt 1KB) {
    Write-Err "Backup failed, abort"
    exit 1
}
$bkSize = [math]::Round((Get-Item $backupFile).Length / 1MB, 2)
Write-Ok "Backup done: $backupFile ($bkSize MB)"

Write-Step "Stage 1: pre-check - table name diff (A dump vs B)"

# Extract table names from A dump (handle UTF-8 encoding)
$aTables = @()
if (Test-Path $DumpFile) {
    $aTables = Get-Content $DumpFile -Encoding UTF8 |
        Select-String -Pattern "^CREATE TABLE\s+`"?([a-zA-Z0-9_]+)`"?" -AllMatches |
        ForEach-Object { $_.Matches[0].Groups[1].Value } |
        Sort-Object -Unique
}

# Query current B table names
$bTablesRaw = & mysql @mysqlArgs $DbName -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='$DbName' ORDER BY table_name;"
$bTables = @($bTablesRaw -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Sort-Object -Unique)

$onlyInA = @($aTables | Where-Object { $bTables -notcontains $_ })
$onlyInB = @($bTables | Where-Object { $aTables -notcontains $_ })
$common  = @($aTables | Where-Object { $bTables -contains $_ })

Write-Host "A(dump) tables: $($aTables.Count)    B(current) tables: $($bTables.Count)    common: $($common.Count)"
if ($onlyInA.Count -gt 0) {
    Write-Warn2 "Tables in A but not in B (will be created by import): $($onlyInA.Count)"
    $onlyInA | ForEach-Object { Write-Host "  + $_" -ForegroundColor DarkGray }
}
if ($onlyInB.Count -gt 0) {
    Write-Warn2 "Tables in B but not in A (kept after import, may be touched by migrate): $($onlyInB.Count)"
    $onlyInB | ForEach-Object { Write-Host "  - $_" -ForegroundColor DarkGray }
}
if ($onlyInA.Count -eq 0 -and $onlyInB.Count -eq 0) {
    Write-Ok "Table names identical"
}
Write-Warn2 "Column-level diff handled by migrate (new columns ALTER ADD automatically)"

if ($WhatIf) {
    Write-Host "`n[Pre-check done. -WhatIf mode stops here.]" -ForegroundColor Magenta
    Write-Host "Backup file kept: $backupFile" -ForegroundColor DarkGray
    exit 0
}

# ---------- Stage 2: rebuild + import ----------
Write-Step "Stage 2: rebuild database and import A dump"
Write-Host "About to DROP DATABASE $DbName and rebuild from dump."
$confirm = Read-Host "Type 'yes' to continue, anything else to cancel"
if ($confirm -ne "yes") {
    Write-Warn2 "Cancelled. DB unchanged. Backup kept: $backupFile"
    exit 0
}

Write-Host "DROP DATABASE..."
& mysql @mysqlArgs -e "DROP DATABASE IF EXISTS $DbName;"
if ($LASTEXITCODE -ne 0) { Write-Err "DROP failed"; exit 1 }

Write-Host "CREATE DATABASE..."
& mysql @mysqlArgs -e "CREATE DATABASE $DbName DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
if ($LASTEXITCODE -ne 0) { Write-Err "CREATE failed"; exit 1 }

Write-Host "Importing dump (large file may take a while)..."
# Use cmd redirection for reliability with large files
$mysqlCmd = "mysql $($mysqlArgs -join ' ') $DbName < `"$DumpFile`""
cmd /c $mysqlCmd
if ($LASTEXITCODE -ne 0) {
    Write-Err "Import failed! Restore with: mysql $($mysqlArgs -join ' ') $DbName < `"$backupFile`""
    exit 1
}
Write-Ok "Import done"

# ---------- Stage 3: git pull + migrate ----------
Write-Step "Stage 3: pull latest code and upgrade schema"
Push-Location $ProjectDir
try {
    Write-Host "git pull..."
    & git pull
    if ($LASTEXITCODE -ne 0) {
        Write-Warn2 "git pull has conflicts. Resolve manually, then run: python manage.py migrate"
        exit 1
    }

    $py = Join-Path $ProjectDir "venv\Scripts\python.exe"
    if (-not (Test-Path $py)) { $py = "python" }

    Write-Host "migrate (applying migrations A doesn't have)..."
    & $py manage.py migrate
    if ($LASTEXITCODE -ne 0) {
        Write-Err "migrate failed! Check showmigrations below, or restore from backup"
        & $py manage.py showmigrations
        exit 1
    }
    Write-Ok "migrate done"
} finally {
    Pop-Location
}

# ---------- Stage 4: verify ----------
Write-Step "Stage 4: verify"

Push-Location $ProjectDir
try {
    $py = Join-Path $ProjectDir "venv\Scripts\python.exe"
    if (-not (Test-Path $py)) { $py = "python" }

    Write-Host "`n[Migration status] ([X]=applied, [ ]=pending)"
    & $py manage.py showmigrations

    Write-Host "`n[Key table row counts] (compare with A original)"
    $tables = @("system_user","system_role","system_menu","system_dept","dict_dict","dict_dictitem",
                "product","bom","bom_list","assembly_recipe","warehouse_log",
                "finish_product","unqualified_item","production_plan","repair")
    foreach ($t in $tables) {
        $cnt = & mysql @mysqlArgs $DbName -N -e "SELECT COUNT(*) FROM $t;" 2>$null
        if ($null -eq $cnt -or $cnt -eq "") { $cnt = "N/A (table missing?)" }
        Write-Host ("  {0,-22} {1}" -f $t, $cnt)
    }
} finally {
    Pop-Location
}

# ---------- Restore hint ----------
Write-Step "Done"
Write-Ok "Database imported from A and upgraded to latest schema"
Write-Host "`nTo rollback to pre-import B state, run:" -ForegroundColor Magenta
Write-Host "  cmd /c `"mysql $($mysqlArgs -join ' ') $DbName < `"$backupFile`"`"" -ForegroundColor Magenta

Write-Host "`nNext: start service and test:" -ForegroundColor Cyan
Write-Host "  cd $ProjectDir" -ForegroundColor DarkGray
Write-Host "  .\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000" -ForegroundColor DarkGray
