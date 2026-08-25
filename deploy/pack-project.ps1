# Pack the whole vue3sys project folder into a customer-ready zip.
# Designed to be called from 打包项目.bat (but can also run directly in PS).
#
# Behavior:
#   - Source: deploy dir's parent (= project root C:\work\vue3sys)
#   - Output: same level as project root, named "vue3sys-deploy.zip"
#   - Keeps: offline_packages, node_modules_offline_bundle, dist, SQL backup, Redis, logs
#   - Drops: node_modules, venv, .git, __pycache__, .pytest_cache, .vite, htmlcov
#   - Warns if youlai_admin_django.sql or offline_packages are missing.

param(
    [string]$SourcePath = '',
    [string]$OutputPath = '',
    [switch]$SkipPrompt
)

$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\_common.ps1"
$paths = Get-ProjectPaths

if ([string]::IsNullOrWhiteSpace($SourcePath)) {
    $SourcePath = $paths.ProjectRoot
}
$SourcePath = [System.IO.Path]::GetFullPath($SourcePath.TrimEnd('\', '/'))

if (-not (Test-Path $SourcePath)) {
    throw "Source path does not exist: $SourcePath"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    # Put zip next to project root so it does not end up re-compressed inside itself
    $parentDir = Split-Path $SourcePath -Parent
    $OutputPath = Join-Path $parentDir 'vue3sys-deploy.zip'
}
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  vue3sys Pack Project" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ("Source     : " + $SourcePath)
Write-Host ("Output zip : " + $OutputPath)
Write-Host ""

# ---- Exclusion list ----
$excludeDirs = @(
    'node_modules',
    'venv',
    '.git',
    '__pycache__',
    '.pytest_cache',
    '.vite',
    'htmlcov'
)
Write-Host "Excluded folder names: $($excludeDirs -join ', ')"
Write-Host ""

# ---- Pre-flight warnings ----
$warnings = @()
$sqlFile = Join-Path $SourcePath 'youlai_admin_django.sql'
if (-not (Test-Path $sqlFile)) {
    $warnings += "[WARNING] Missing youlai_admin_django.sql in project root. Customer deploy will be UNABLE to initialize the database."
}
$offlineDir = Join-Path $SourcePath (Join-Path 'youlai-django' 'offline_packages')
if (-not (Test-Path $offlineDir)) {
    $warnings += "[TIP]     Missing youlai-django\offline_packages\. If this is for OFFLINE customer machines, run deploy\pack-offline-deps.ps1 first."
}
if ($warnings.Count -gt 0) {
    foreach ($w in $warnings) { Write-Host $w -ForegroundColor Yellow }
    Write-Host ""
}

# ---- Stage copy using robocopy (robocopy mirrors to a temp dir, with exclusions) ----
Write-Step "Staging files (robocopy)"
$stage = Join-Path $env:TEMP ("vue3sys-pack-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage -Force | Out-Null
Write-Host "Stage dir: $stage"

# robocopy return codes 0..7 are "ok" (0=no copy, 1=files copied, etc); 8+ are errors
$robocopyLog = Join-Path $paths.LogDir ("pack-robocopy_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
Initialize-LogDir $paths.LogDir
& robocopy $SourcePath $stage /E /XD $excludeDirs /R:1 /W:1 /NFL /NDL /NJH /NJS /nc /ns /np /UNILOG:$robocopyLog
$rc = $LASTEXITCODE
if ($rc -ge 8) {
    throw "robocopy failed with exit code $rc. See log: $robocopyLog"
}
Write-Ok "Staged (robocopy exit $rc). Log: $robocopyLog"

# ---- Compress ----
Write-Step "Compressing"
if (Test-Path $OutputPath) {
    Write-Warn "Removing existing zip: $OutputPath"
    Remove-Item $OutputPath -Force -ErrorAction Stop
}
$payload = Join-Path $stage '*'
Write-Host "Running Compress-Archive (can take several minutes if dist/ or offline bundles are present)..."
Compress-Archive -Path $payload -DestinationPath $OutputPath -CompressionLevel Optimal -ErrorAction Stop

# Report
$zipItem = Get-Item $OutputPath
$sizeMB = [math]::Round($zipItem.Length / 1MB, 1)
Write-Ok ("Zip created: " + $OutputPath)
Write-Host ("  Size : " + $sizeMB + " MB") -ForegroundColor Gray
Write-Host ("  Time : " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) -ForegroundColor Gray

# ---- Cleanup stage ----
Write-Step "Cleanup stage dir"
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
Write-Ok "Stage dir removed"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  PACK COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps (copy to customer machine):" -ForegroundColor Yellow
Write-Host "  1. Copy $OutputPath to target PC (any drive is OK: C:\ or D:\)"
Write-Host "  2. Extract zip anywhere (project name folder will contain: deploy\, youlai-django\, vue3-element-admin\, Redis\)"
Write-Host "  3. Right-click  deploy\一键部署-全自动.bat  ->  Run as administrator"
Write-Host "  4. After success banner, open:  http://localhost:3000"
Write-Host ""
exit 0
