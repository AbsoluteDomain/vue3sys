# vue3sys deploy menu (ASCII-only for Windows Server / GBK)

param(
    [ValidateSet('', 'all', 'prereq', 'check', 'configure', 'install', 'import', 'verify', 'start', 'fresh')]
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
    Write-Host "  Fresh PC: run 1 or 9 first" -ForegroundColor Yellow
    Write-Host ""
    Write-Host '  1. Install prerequisites   - Python, Node, MySQL, pnpm'
    Write-Host '  2. Check environment       -> check-env.ps1'
    Write-Host '  3. Generate config         -> configure.ps1'
    Write-Host '  4. Install project deps    -> install-deps.ps1'
    Write-Host '  5. Import database         -> import-database.ps1'
    Write-Host '  6. Verify services         -> verify-services.ps1'
    Write-Host '  7. Start all services      -> start-all.ps1'
    Write-Host '  8. Deploy steps 3-5        -> config + deps + import'
    Write-Host '  9. Full fresh deploy       -> prereq + steps 3-5'
    Write-Host '  r. Recreate venv           -> after copy from another PC'
    Write-Host '  0. Exit'
    Write-Host ""
}

function Invoke-Step {
    param(
        [string]$ScriptName,
        [string[]]$ExtraArgs = @()
    )
    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    if (-not (Test-Path $scriptPath)) {
        throw "Script not found: $scriptPath"
    }
    if ($ExtraArgs.Count -gt 0) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath @ExtraArgs
    } else {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath
    }
    if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
        Write-Host "Step $ScriptName exit code: $LASTEXITCODE" -ForegroundColor Yellow
    }
}

function Run-DeployCore {
    Invoke-Step 'configure.ps1'
    Invoke-Step 'install-deps.ps1'
    $import = Read-Host "Import youlai_admin_django.sql? (Y/n)"
    if ($import -ne 'n' -and $import -ne 'N') {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'import-database.ps1') -CreateDatabase
    }
    Invoke-Step 'check-env.ps1'
}

function Run-FreshDeploy {
    Write-Host ""
    Write-Host "Full deploy: prerequisites -> config -> deps -> import" -ForegroundColor Cyan
    if (-not (Test-IsAdmin)) {
        Write-Warn "Recommend: run install-prerequisites bat as Administrator first"
        $go = Read-Host "Continue anyway? (Y/n)"
        if ($go -eq 'n' -or $go -eq 'N') { return }
    }
    Invoke-Step 'install-prerequisites.ps1' -ExtraArgs @('-InstallAll')
    Run-DeployCore
}

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

while ($true) {
    Show-Menu
    $choice = Read-Host "Choice"
    switch ($choice) {
        '1' { Invoke-Step 'install-prerequisites.ps1' }
        '2' { Invoke-Step 'check-env.ps1' }
        '3' { Invoke-Step 'configure.ps1' }
        '4' { Invoke-Step 'install-deps.ps1' }
        '5' { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'import-database.ps1') -CreateDatabase }
        '6' { Invoke-Step 'verify-services.ps1' }
        '7' { Invoke-Step 'start-all.ps1' }
        '8' { Run-DeployCore }
        '9' { Run-FreshDeploy }
        'r' { Invoke-Step 'recreate-venv.ps1' }
        'R' { Invoke-Step 'recreate-venv.ps1' }
        '0' { break }
        default { Write-Host "Invalid choice" -ForegroundColor Red }
    }
    Read-Host "Press Enter to continue"
}
