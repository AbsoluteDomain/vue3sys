# Pack offline dependencies for customer deploy (run on a machine WITH internet).
#
# What it does:
#   1. Downloads ALL Python wheels matching requirements.txt into
#      youlai-django\offline_packages\  (install-deps.ps1 installs from here with --no-index)
#   2. Installs frontend deps into node_modules OFFLINE-SAFE (resolves all versions)
#      and creates:
#         - vue3-element-admin\node_modules_offline_bundle\  (exact copy of node_modules)
#           install-deps.ps1 will RESTORE node_modules from this bundle when node_modules
#           doesn't exist and there's no internet.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\pack-offline-deps.ps1
#
# IMPORTANT: run on same Python major.minor (e.g. 3.13) and same Windows x64 as
# the target machine, otherwise pip wheel abi mismatches will cause offline install to fail.

param(
    [switch]$SkipFrontend,
    [switch]$UseUv
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths

Write-Step "=== Pack Offline Dependencies (Python + Frontend) ==="

$reqFile = Join-Path $paths.BackendRoot 'requirements.txt'
if (-not (Test-Path $reqFile)) {
    throw "requirements.txt not found: $reqFile"
}

# =================================================================
# Part 1: Python wheels
# =================================================================
Write-Step "Part 1/2: Pack Python wheels"

$outDir = Join-Path $paths.BackendRoot 'offline_packages'
if (Test-Path $outDir) {
    Write-Warn "Cleaning existing offline_packages"
    Remove-Item -Path $outDir -Recurse -Force
}
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

if (-not (Test-CommandExists 'python')) {
    throw "python not found. Install Python and add to PATH"
}

Write-Host "Downloading wheels to: $outDir"
Write-Host "This may take several minutes..."
Write-Host ""

# Use a temporary venv to avoid polluting the system
$tempVenv = Join-Path $env:TEMP ("venv_offline_pack_" + [guid]::NewGuid().ToString('N'))
Write-Step "Create temp venv for clean download"
& python -m venv $tempVenv
$tempPip = Join-Path $tempVenv 'Scripts\pip.exe'
$tempPython = Join-Path $tempVenv 'Scripts\python.exe'

Write-Step "Download wheels"
& $tempPip install --upgrade pip

$useUvPack = $UseUv -or (Test-CommandExists 'uv')
if ($useUvPack -and (Test-CommandExists 'uv')) {
    Write-Ok "Using uv pip download (faster)"
    & uv pip download --python $tempPython -d $outDir -r $reqFile
} else {
    & $tempPip download -d $outDir -r $reqFile
}

if ($LASTEXITCODE -ne 0) {
    Write-Fail "pip download failed"
    Remove-Item -Path $tempVenv -Recurse -Force -ErrorAction SilentlyContinue
    throw "Failed to download wheels"
}

# Cleanup temp venv
Remove-Item -Path $tempVenv -Recurse -Force -ErrorAction SilentlyContinue

$wheelCount = (Get-ChildItem -Path $outDir -Filter '*.whl' -ErrorAction SilentlyContinue).Count
$tarCount = (Get-ChildItem -Path $outDir -Filter '*.tar.gz' -ErrorAction SilentlyContinue).Count
$totalSize = (Get-ChildItem -Path $outDir -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB

Write-Host ""
Write-Ok "Python offline packages ready: $outDir"
Write-Host "  Wheels: $wheelCount"
Write-Host "  Tar.gz: $tarCount"
Write-Host "  Total:  $([math]::Round($totalSize, 1)) MB"

# =================================================================
# Part 2: Frontend node_modules offline bundle
# =================================================================
if (-not $SkipFrontend) {
    Write-Step "Part 2/2: Pack frontend offline bundle (node_modules_offline_bundle)"

    if (-not (Test-CommandExists 'pnpm')) {
        if (Test-CommandExists 'npm') {
            Write-Step "Install pnpm globally first"
            & npm install -g pnpm
            Refresh-SessionPath
            if (-not (Test-CommandExists 'pnpm')) {
                throw "pnpm still not found after npm install -g"
            }
        } else {
            Write-Warn "No pnpm and no npm. Skipping frontend offline bundle."
        }
    }

    if (Test-CommandExists 'pnpm') {
        Push-Location $paths.FrontendRoot
        try {
            # Clean old node_modules to get a reproducible state
            $nm = Join-Path $paths.FrontendRoot 'node_modules'
            if (Test-Path $nm) {
                Write-Warn "Removing existing node_modules for clean offline pack"
                Remove-Item $nm -Recurse -Force
            }
            # Fresh install with frozen lockfile to avoid picking up uncommitted changes
            Write-Host "Running pnpm install --frozen-lockfile (or pnpm install if lockfile missing)..."
            $lockFile = Join-Path $paths.FrontendRoot 'pnpm-lock.yaml'
            if (Test-Path $lockFile) {
                & pnpm install --frozen-lockfile
            } else {
                & pnpm install
            }
            if ($LASTEXITCODE -ne 0) { throw "pnpm install failed" }

            # Copy node_modules to node_modules_offline_bundle (next to frontend root, not in backend)
            $bundle = Join-Path $paths.FrontendRoot 'node_modules_offline_bundle'
            if (Test-Path $bundle) { Remove-Item $bundle -Recurse -Force }
            Write-Host "Copying node_modules to node_modules_offline_bundle..."
            Copy-Item -Path $nm -Destination $bundle -Recurse -Force

            $nmSize = (Get-ChildItem $bundle -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB
            $nmFileCount = (Get-ChildItem $bundle -Recurse -File -ErrorAction SilentlyContinue).Count
            Write-Ok "Frontend offline bundle ready: $bundle"
            Write-Host "  Files: $nmFileCount"
            Write-Host "  Total: $([math]::Round($nmSize, 1)) MB"

            # Cleanup the live node_modules (customers will restore from bundle via install-deps.ps1)
            Write-Host "Cleaning live node_modules (will be restored from bundle on target server)..."
            Remove-Item $nm -Recurse -Force
        } finally {
            Pop-Location
        }
    }
}

Write-Host ""
Write-Ok "Offline pack COMPLETE"
Write-Host ""
Write-Host "Copy these folders along with the project zip to target server:" -ForegroundColor Yellow
Write-Host "  Python  : $outDir" -ForegroundColor Gray
if (-not $SkipFrontend) {
    Write-Host "  Frontend: $(Join-Path $paths.FrontendRoot 'node_modules_offline_bundle')" -ForegroundColor Gray
}
Write-Host ""
Write-Host "On target server, run 一键部署-全自动.bat (as Administrator) to deploy." -ForegroundColor Yellow

