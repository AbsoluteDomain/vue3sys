# vue3sys deploy menu (ASCII-only for Windows Server / GBK)

param(
    [ValidateSet('', 'all', 'prereq', 'check', 'configure', 'install', 'import', 'verify', 'start', 'update', 'fresh', 'pack', 'switch', 'auto', 'build')]
    [string]$Action = ''
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
. "$PSScriptRoot\_common.ps1"

function Show-Menu {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  vue3sys Deploy Menu" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Fresh PC: run 1 or A first (needs Admin)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host '  1. Install prerequisites   - Python, Node, MySQL, pnpm (needs Admin)'
    Write-Host '  2. Check environment       -> check-env.ps1'
    Write-Host '  3. Generate config         -> configure.ps1'
    Write-Host '  4. Install project deps    -> install-deps.ps1 (venv + pip + pnpm)'
    Write-Host '  5. Import database         -> import-database.ps1 (plus migrate + collectstatic)'
    Write-Host '  6. Verify services         -> verify-services.ps1'
    Write-Host '  7. Start all services      -> start-all.ps1 (Redis + Django + Frontend)'
    Write-Host '  8. Deploy steps 3~5        -> config + deps (skip migrate) + import + migrate + collectstatic'
    Write-Host '  9. Full fresh deploy       -> prereq -> steps 3~5 (after: choose 7 or A to start)'
    Write-Host '  A. Unattended full deploy  -> prereq (Admin) -> defaults config -> deps -> import -> start'
    Write-Host '  B. Build frontend for Nginx-> pnpm build + dist/ ready for production'
    Write-Host '  u. Update from Git          -> pull + deps + migrate + restart'
    Write-Host '  r. Recreate venv           -> after copy from another PC'
    Write-Host '  p. Pack offline deps       -> download wheels + frontend node_modules for offline deploy'
    Write-Host '  g. Switch git remote       -> GitHub <-> Gitea'
    Write-Host '  0. Exit'
    Write-Host ""
}

function Invoke-Step {
    param(
        [string]$ScriptName,
        [string[]]$ExtraArgs = @(),
        [string]$TeeLog = ''
    )
    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    if (-not (Test-Path $scriptPath)) {
        throw "Script not found: $scriptPath"
    }

    $argList = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$scriptPath) + $ExtraArgs

    if ($TeeLog) {
        # Tee to a file AND the console. Use & operator to run powershell and capture output
        # through Tee-Object. For stderr we redirect via 2>&1 inside the tee pipeline.
        $output = & powershell.exe @argList 2>&1 | Tee-Object -FilePath $TeeLog -Append
        $exitCode = $LASTEXITCODE
    } else {
        $output = & powershell.exe @argList 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    }

    if ($exitCode -ne 0 -and $null -ne $exitCode) {
        Write-Warn "Step $ScriptName exit code: $exitCode"
    }
    return [PSCustomObject]@{
        ExitCode = $exitCode
        Output   = $output
    }
}

function Run-DeployCore {
    param(
        [switch]$UseDefaults,
        [switch]$AutoStart,
        [string]$TeeLog = ''
    )
    function RequireOk {
        param($StepResult, [string]$StepName)
        if ($null -eq $StepResult -or $StepResult.ExitCode -ne 0) {
            $code = if ($StepResult) { $StepResult.ExitCode } else { 'null' }
            Write-Fail "Run-DeployCore STOPPED early at step: $StepName (exit=$code)"
            if (-not [string]::IsNullOrWhiteSpace($TeeLog)) {
                Write-Host "   Full log: $TeeLog" -ForegroundColor Yellow
            }
            throw "Deploy step failed: $StepName (exit=$code)"
        }
        Write-Ok "Step $StepName OK"
    }

    $configureArgs = @()
    if ($UseDefaults) { $configureArgs += @('-Force','-UseDefaults') }
    $r = Invoke-Step -ScriptName 'configure.ps1' -ExtraArgs $configureArgs -TeeLog $TeeLog
    RequireOk -StepResult $r -StepName 'configure.ps1'

    $r = Invoke-Step -ScriptName 'install-deps.ps1' -ExtraArgs @('-SkipMigrate') -TeeLog $TeeLog
    RequireOk -StepResult $r -StepName 'install-deps.ps1'

    # Venv presence hard check (the thing the user reported missing)
    $paths = Get-ProjectPaths
    if (-not (Test-Path $paths.VenvPython)) {
        throw "[FATAL] install-deps.ps1 returned success but venv python MISSING: $($paths.VenvPython). Check logs in $($paths.LogDir)"
    }
    Write-Ok "Venv presence confirmed: $($paths.VenvPython)"

    if (-not $UseDefaults) {
        $import = Read-Host "Import youlai_admin_django.sql? (Y/n)"
        if ($import -eq 'n' -or $import -eq 'N') {
            Write-Warn "Skipped DB import. MUST run install-deps.ps1 again (without -SkipMigrate) to complete migrate."
            return
        }
    }

    $importArgs = @('-CreateDatabase')
    if ($UseDefaults) { $importArgs += @('-AutoImport') }
    $r = Invoke-Step -ScriptName 'import-database.ps1' -ExtraArgs $importArgs -TeeLog $TeeLog
    RequireOk -StepResult $r -StepName 'import-database.ps1'

    $r = Invoke-Step -ScriptName 'check-env.ps1' -TeeLog $TeeLog
    RequireOk -StepResult $r -StepName 'check-env.ps1'

    if ($AutoStart) {
        $r = Invoke-Step -ScriptName 'start-all.ps1' -TeeLog $TeeLog
        RequireOk -StepResult $r -StepName 'start-all.ps1'
        $r = Invoke-Step -ScriptName 'verify-services.ps1' -TeeLog $TeeLog
        RequireOk -StepResult $r -StepName 'verify-services.ps1'
    }
}

function Run-FreshDeploy {
    Write-Host ""
    Write-Host "Full deploy: prerequisites -> config -> deps -> import" -ForegroundColor Cyan
    if (-not (Test-IsAdmin)) {
        Write-Warn "Recommend: run install-prerequisites bat as Administrator first"
        $go = Read-Host "Continue anyway? (Y/n)"
        if ($go -eq 'n' -or $go -eq 'N') { return }
    }
    Invoke-Step 'install-prerequisites.ps1' -ExtraArgs @('-InstallAll') | Out-Null
    Run-DeployCore
}

function Run-Unattended {
    # Fully automated: Admin install prereq -> defaults config -> deps -> import -> start.
    # Designed for customer PCs: DOUBLE-CLICK and walk away.
    $paths = Get-ProjectPaths
    Initialize-LogDir $paths.LogDir
    $teeLog = Join-Path $paths.LogDir ("deploy-unattended_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
    New-Item -ItemType File -Path $teeLog -Force | Out-Null
    $banner = @"

===========================================================
  UNATTENDED FULL DEPLOY  (started: $("{0:yyyy-MM-dd HH:mm:ss}" -f (Get-Date)))
  Full tee log: $teeLog
===========================================================
"@
    Write-Host $banner -ForegroundColor Cyan
    $banner | Out-File $teeLog -Append -Encoding utf8 -ErrorAction SilentlyContinue

    try {
        # --- Step 1: Prerequisites ---
        if (Test-IsAdmin) {
            Write-Ok "Running as Administrator -> install prerequisites if missing"
            $r = Invoke-Step -ScriptName 'install-prerequisites.ps1' -ExtraArgs @('-InstallAll') -TeeLog $teeLog
            if ($r.ExitCode -ne 0) {
                Write-Warn "install-prerequisites exit=$($r.ExitCode) (some components may need manual install; continuing to run resolver anyway)"
            }
        } else {
            Write-Warn "NOT running as Administrator.  Skipping winget-based prerequisite install."
            Write-Host "If this is a FRESH customer PC, right-click 一键部署-全自动.bat -> Run as Administrator, then re-run." -ForegroundColor Yellow
        }
        # Always run resolver again: catches "customer manually installed Node/MySQL but PATH not refreshed in this bat session"
        "`n[post-prereq] Resolve-PrerequisitePaths ..." | Out-File $teeLog -Append -Encoding utf8 -ErrorAction SilentlyContinue
        $resolved = Resolve-PrerequisitePaths
        $resolved | Out-File $teeLog -Append -Encoding utf8 -ErrorAction SilentlyContinue
        Write-Host ("[Resolver] AllFound={0}  Python={1}  Node={2}  pnpm={3}  MySQL={4}" -f `
            $resolved.AllFound,$resolved.PythonBinDir,$resolved.NodeBinDir,$resolved.PnpmBinDir,$resolved.MySqlBinDir) -ForegroundColor Gray

        if (-not $resolved.AllFound) {
            Write-Fail "Resolver still missing some components. Please check & install manually, then rerun:"
            if (-not $resolved.PythonBinDir) { Write-Host "  - Python 3.10-3.14 (x64 installer -> Add to PATH)" -ForegroundColor Red }
            if (-not $resolved.NodeBinDir)   { Write-Host "  - Node.js 20.19+ (x64 installer)" -ForegroundColor Red }
            if (-not $resolved.PnpmBinDir)    { Write-Host "  - pnpm (open cmd as Admin: npm install -g pnpm)" -ForegroundColor Red }
            if (-not $resolved.MySqlBinDir)   { Write-Host "  - MySQL Server 8 (with MySQL client -> add bin to PATH)" -ForegroundColor Red }
            Write-Host "Full resolver log in: $teeLog" -ForegroundColor Yellow
            throw "Missing prerequisite resolvers. Stopped BEFORE venv creation."
        }

        # --- Step 2..N: config + install-deps (create venv + pip/pnpm) + import + start ---
        Run-DeployCore -UseDefaults -AutoStart -TeeLog $teeLog

        # Final venv confirmation (for the user to confirm in log)
        $paths = Get-ProjectPaths
        $confirm = @"

===========================================================
  UNATTENDED DEPLOY SUCCESS  ($("{0:yyyy-MM-dd HH:mm:ss}" -f (Get-Date)))
  Web UI : http://localhost:3000
  API    : http://localhost:8000
  venv   : $($paths.VenvPython)
  Full log: $teeLog
  Default credentials:
    MySQL    root / root     (change in .env)
    Redis    123456          (change in .env + redis.windows.conf)
===========================================================
"@
        Write-Host $confirm -ForegroundColor Green
        $confirm | Out-File $teeLog -Append -Encoding utf8 -ErrorAction SilentlyContinue
        exit 0
    } catch {
        $errText = @"

===========================================================
  UNATTENDED DEPLOY FAILED  ($("{0:yyyy-MM-dd HH:mm:ss}" -f (Get-Date)))
  Reason: $($_.Exception.Message)
  Full log: $teeLog
  Also check: $($paths.LogDir)install-deps_*.log / pack-robocopy_*.log
-----------------------------------------------------------
  Next steps:
   1. Open the log file above in Notepad and scroll to bottom.
   2. If install-deps failed and says "python not found", install Python 3.10-3.14
      with "Add Python to PATH" checked, CLOSE this window and re-open deploy bat.
   3. If venv was not created, run: powershell -File deploy\recreate-venv.ps1
   4. After fixing issues, re-run 一键部署-全自动.bat (Admin) to continue.
===========================================================
"@
        Write-Host $errText -ForegroundColor Red
        try { $errText | Out-File $teeLog -Append -Encoding utf8 -ErrorAction SilentlyContinue } catch {}
        exit 1
    }
}

function Build-Frontend {
    Write-Step "Build frontend for production (Nginx deploy: dist/)"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'build-frontend.ps1')
}

# CLI action shortcuts
if ($Action -eq 'auto')  { Run-Unattended; exit 0 }
if ($Action -eq 'build') { Build-Frontend;  exit 0 }
if ($Action -eq 'fresh') { Run-FreshDeploy; exit 0 }
if ($Action -eq 'prereq') { Invoke-Step 'install-prerequisites.ps1'; exit 0 }
if ($Action -eq 'all') { Run-DeployCore; exit 0 }
if ($Action -eq 'check') { Invoke-Step 'check-env.ps1'; exit 0 }
if ($Action -eq 'configure') { Invoke-Step 'configure.ps1'; exit 0 }
if ($Action -eq 'install') { Invoke-Step 'install-deps.ps1'; exit 0 }
if ($Action -eq 'import') {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'import-database.ps1') -CreateDatabase
    exit 0
}
if ($Action -eq 'verify') { Invoke-Step 'verify-services.ps1'; exit 0 }
if ($Action -eq 'start') { Invoke-Step 'start-all.ps1'; exit 0 }
if ($Action -eq 'update') { Invoke-Step 'update.ps1'; exit 0 }
if ($Action -eq 'pack') { Invoke-Step 'pack-offline-deps.ps1'; exit 0 }
if ($Action -eq 'switch') { Invoke-Step 'switch-remote.ps1'; exit 0 }

while ($true) {
    Show-Menu
    $choice = Read-Host "Choice"
    switch -CaseSensitive ($choice) {
        '1' { Invoke-Step 'install-prerequisites.ps1' }
        '2' { Invoke-Step 'check-env.ps1' }
        '3' { Invoke-Step 'configure.ps1' }
        '4' { Invoke-Step 'install-deps.ps1' }
        '5' { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'import-database.ps1') -CreateDatabase }
        '6' { Invoke-Step 'verify-services.ps1' }
        '7' { Invoke-Step 'start-all.ps1' }
        '8' { Run-DeployCore }
        '9' { Run-FreshDeploy }
        'A' { Run-Unattended }
        'a' { Run-Unattended }
        'B' { Build-Frontend }
        'b' { Build-Frontend }
        'u' { Invoke-Step 'update.ps1' }
        'U' { Invoke-Step 'update.ps1' }
        'r' { Invoke-Step 'recreate-venv.ps1' }
        'R' { Invoke-Step 'recreate-venv.ps1' }
        'p' { Invoke-Step 'pack-offline-deps.ps1' }
        'P' { Invoke-Step 'pack-offline-deps.ps1' }
        'g' { Invoke-Step 'switch-remote.ps1' }
        'G' { Invoke-Step 'switch-remote.ps1' }
        '0' { break }
        default { Write-Host "Invalid choice" -ForegroundColor Red }
    }
    if ($choice -ne '0') {
        Read-Host "Press Enter to continue"
    }
}
