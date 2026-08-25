# Install venv, pip, pnpm (ASCII-only)
# Supports:
#   - Offline install: place wheels in youlai-django\offline_packages\
#   - uv mode (faster): use -UseUv; creates standard venv fully compatible with pip

param(
    [switch]$SkipFrontend,
    [switch]$RecreateVenv,
    [switch]$Offline,
    [switch]$UseUv,
    [switch]$SkipMigrate
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths
Initialize-LogDir $paths.LogDir
$logFile = Join-Path $paths.LogDir ("install-deps_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
"START install-deps at $(Get-Date -Format s)" | Out-File $logFile -Encoding utf8 -Append

function Trace {
    param([string]$Line)
    $stamped = "[$(Get-Date -Format 'HH:mm:ss')] $Line"
    Write-Host $stamped
    $stamped | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
}
Trace "Log file: $logFile"

Trace "Run Resolver -> ensure Python / Node / pnpm / MySQL are visible in current session PATH"
$null = Resolve-PrerequisitePaths
$config = Get-PrerequisitesConfig

$pythonOk = Test-PythonVersionOk -Config $config
if (-not $pythonOk -and -not (Test-CommandExists 'python')) {
    Trace "[FATAL] python.exe not on PATH and resolver could not find Python install dir."
    Trace "  - Install Python 3.10-3.14 first (use deploy\install-prerequisites.ps1 as Admin)."
    Trace "  - After install, close this window and re-open deploy bat (to refresh PATH)."
    Trace "  - Or run PowerShell command:  Resolve-PrerequisitePaths  to debug detection."
    throw "Python not found. See log: $logFile"
}

$pySource = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($pySource) { Trace "Using host python: $pySource" } else { Trace "[WARN] Get-Command python failed (rare); falling back to PATH python." }

$venvDir = Join-Path $paths.BackendRoot 'venv'
Trace "Target venv dir: $venvDir"

function Test-VenvUsable {
    param([string]$ExpectedVenvDir)
    $py = Join-Path $ExpectedVenvDir 'Scripts\python.exe'
    if (-not (Test-Path $py)) { Trace "Test-VenvUsable: $py missing"; return $false }
    try {
        $out = & $py --version 2>&1
        $code = $LASTEXITCODE
        $outStr = ($out | Out-String).Trim()
        "Test-VenvUsable py=$py code=$code out=$outStr" | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
        if ($code -eq 0 -and $outStr -match 'Python') {
            Trace "Venv usable: $outStr ($py)"
            return $true
        }
        Trace "Test-VenvUsable: bad exit=$code or output=$outStr"
        return $false
    } catch {
        Trace "Test-VenvUsable exception: $($_.Exception.Message)"
        return $false
    }
}

if ($RecreateVenv -and (Test-Path $venvDir)) {
    Trace "RecreateVenv=true -> remove existing venv folder"
    try {
        Remove-Item -Path $venvDir -Recurse -Force -ErrorAction Stop
        Trace "Removed old venv"
    } catch {
        Trace "[FATAL] Failed to remove old venv: $($_.Exception.Message)"
        Trace "  Close any process locking venv (IDEs running python.exe, Django, etc.) then rerun."
        throw
    }
}

Trace "Step: Create Python venv"
if (-not (Test-VenvUsable -ExpectedVenvDir $venvDir)) {
    if (Test-Path $venvDir) {
        Trace "[WARN] Broken venv detected (python.exe missing / not runnable). Removing..."
        try { Remove-Item -Path $venvDir -Recurse -Force -ErrorAction Stop }
        catch {
            Trace "[FATAL] Cannot clean broken venv: $($_.Exception.Message)"
            Trace "  Make sure nothing is locking $venvDir . Close editors and try again."
            throw
        }
    }

    Trace "Creating NEW venv at: $venvDir"
    $useUv = $UseUv -or (Test-CommandExists 'uv')
    if ($useUv) {
        Trace "Using uv venv (faster)"
        & uv venv $venvDir --seed 2>&1 | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
        & uv venv $venvDir --seed 2>&1 | Out-Host
    } else {
        Trace "Using python -m venv"
        & python -m venv $venvDir 2>&1 | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
        & python -m venv $venvDir 2>&1 | Out-Host
    }
    $createExit = $LASTEXITCODE
    Trace "venv creation exit code: $createExit"

    # Post-create hard validation: venv folder + Scripts\python.exe MUST exist and run.
    if (-not (Test-Path $venvDir)) {
        throw "[FATAL] python -m venv exited with $createExit but venv folder NOT created. Log: $logFile"
    }
    if (-not (Test-Path (Join-Path $venvDir 'Scripts\python.exe'))) {
        throw "[FATAL] venv directory created but Scripts\python.exe missing. Path: $venvDir"
    }
    if (-not (Test-VenvUsable -ExpectedVenvDir $venvDir)) {
        throw "[FATAL] Venv created but Scripts\python.exe is not runnable. Check antivirus / Windows Defender blocking python.exe inside $venvDir"
    }
    Trace "Venv CREATE OK"
} else {
    Trace "Existing venv already usable. Skip create."
}
# Extra public safety check BEFORE pip install: verify $paths.VenvPython points to a real file.
if (-not (Test-Path $paths.VenvPython)) {
    throw "[FATAL] ProjectPaths.VenvPython does not exist: $($paths.VenvPython). Investigate venv dir layout."
}
Trace "Venv python confirmed: $($paths.VenvPython)"

Trace "Step: Install Python packages"
Push-Location $paths.BackendRoot

# Detect offline packages automatically
$offlineDir = Join-Path $paths.BackendRoot 'offline_packages'
$useOffline = $Offline -or (Test-Path $offlineDir)
$useUv = $UseUv -or (Test-CommandExists 'uv')

if ($useUv) {
    Trace "Using uv pip install (faster)"
    if ($useOffline -and (Test-Path $offlineDir)) {
        Trace "Offline install from: $offlineDir"
        & uv pip install --python $paths.VenvPython --find-links $offlineDir -r requirements.txt 2>&1 | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
        & uv pip install --python $paths.VenvPython --find-links $offlineDir -r requirements.txt
    } else {
        if ($Offline) { Trace "[WARN] -Offline but offline_packages missing; fallback to online" }
        & uv pip install --python $paths.VenvPython -r requirements.txt 2>&1 | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
        & uv pip install --python $paths.VenvPython -r requirements.txt
    }
} else {
    Trace "Upgrade pip in venv first"
    & $paths.VenvPip install --upgrade pip 2>&1 | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
    & $paths.VenvPip install --upgrade pip
    if ($useOffline -and (Test-Path $offlineDir)) {
        Trace "Offline install from: $offlineDir"
        & $paths.VenvPip install --no-index --find-links=$offlineDir -r requirements.txt 2>&1 | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
        & $paths.VenvPip install --no-index --find-links=$offlineDir -r requirements.txt
    } else {
        if ($Offline) { Trace "[WARN] -Offline but offline_packages missing; fallback to online" }
        & $paths.VenvPip install -r requirements.txt 2>&1 | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
        & $paths.VenvPip install -r requirements.txt
    }
}
$pipExit = $LASTEXITCODE
Trace "pip install exit code: $pipExit"
if ($pipExit -ne 0) {
    Pop-Location
    throw "[FATAL] pip install failed (exit=$pipExit). Full log: $logFile"
}
# Confirm a known package installed successfully
try {
    $showDjango = & $paths.VenvPip show django 2>&1
    $showExit = $LASTEXITCODE
    if ($showExit -ne 0 -or -not ($showDjango -match 'Name: Django|Name: Django')) {
        Trace "[WARN] pip show django reported non-zero or unexpected output (non-fatal if Django not needed; usually a bug)"
        $showDjango | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
    }
} catch {}
Pop-Location
Trace "Python deps installed"

Trace "Step: Django check (connectivity to DB via .env)"
Push-Location $paths.BackendRoot
$checkOut = & $paths.VenvPython manage.py check 2>&1
$checkExit = $LASTEXITCODE
($checkOut | Out-String) | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
$checkOut | Out-Host
if ($checkExit -ne 0) {
    Pop-Location
    throw "[FATAL] django check failed (exit=$checkExit). Check .env DB settings or import database first. Log: $logFile"
}
Pop-Location
Trace "django check OK"

if (-not $SkipMigrate) {
    Trace "Step: Django migrate"
    Push-Location $paths.BackendRoot
    $migOut = & $paths.VenvPython manage.py migrate --noinput 2>&1
    $migExit = $LASTEXITCODE
    ($migOut | Out-String) | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
    $migOut | Out-Host
    Pop-Location
    if ($migExit -ne 0) {
        throw "[FATAL] migrate failed (exit=$migExit). Log: $logFile"
    }
    Trace "migrate OK"
} else {
    Trace "SkipMigrate: defer migrate -> will be executed by import-database.ps1 AFTER SQL import"
}

if (-not $SkipFrontend) {
    Trace "Step: Install frontend deps"
    $nodeModules = Join-Path $paths.FrontendRoot 'node_modules'
    if (Test-Path $nodeModules) {
        Trace "[WARN] node_modules already exists; if it was copied from another machine, delete it and rerun"
    }
    if (-not (Test-CommandExists 'pnpm')) {
        Trace "[WARN] pnpm not found, trying: npm install -g pnpm"
        if (Test-CommandExists 'npm') {
            & npm install -g pnpm
        } else {
            throw "[FATAL] Install Node.js and pnpm first (Resolver should have added to PATH). Re-run deploy as Admin and check logs."
        }
    }
    Push-Location $paths.FrontendRoot
    # Auto-detect offline frontend cache
    $offlineNodeBundle = Join-Path $paths.FrontendRoot 'node_modules_offline_bundle'
    if ((Test-Path $offlineNodeBundle) -and -not (Test-Path $nodeModules)) {
        Trace "Offline: restore node_modules from node_modules_offline_bundle"
        Copy-Item -Path $offlineNodeBundle -Destination $nodeModules -Recurse -Force
    }
    Trace "pnpm install..."
    & pnpm install 2>&1 | Out-File $logFile -Append -Encoding utf8 -ErrorAction SilentlyContinue
    & pnpm install
    $pnpmExit = $LASTEXITCODE
    Trace "pnpm install exit code: $pnpmExit"
    Pop-Location
    if ($pnpmExit -ne 0) {
        throw "[FATAL] pnpm install failed (exit=$pnpmExit). Log: $logFile"
    }
    Trace "Frontend deps installed"
}

Trace "FINISHED install-deps (all steps succeeded)"
Trace "  - Backend venv: $($paths.VenvPython)"
Trace "  - Frontend node_modules: $(Join-Path $paths.FrontendRoot 'node_modules')"
Trace "  - Full log: $logFile"
Write-Host ""
Write-Ok "Done. Next: import-database.ps1 (or start-all.ps1)"
exit 0
