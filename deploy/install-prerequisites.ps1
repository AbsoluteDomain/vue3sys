# Install Python / Node.js / MySQL / pnpm (ASCII-only for PowerShell 5.1)

param(
    [switch]$CheckOnly,
    [switch]$InstallAll,
    [switch]$SkipMySQL,
    [switch]$SkipVcRedist
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

$logDir = Join-Path $script:DeployScriptRoot 'logs'
Initialize-LogDir $logDir
$logFile = Join-Path $logDir ("install-prerequisites_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

function Write-Log {
    param([string]$Message)
    Add-Content -Path $logFile -Value ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message) -Encoding UTF8
}

trap {
    Write-Fail $_.Exception.Message
    Write-Log "ERROR: $($_.Exception.Message)"
    Write-Log $_.ScriptStackTrace
    Write-Host ""
    Write-Host "Log file: $logFile" -ForegroundColor Yellow
    Write-Host "Deploy dir: $script:DeployScriptRoot" -ForegroundColor Gray
    exit 1
}

Write-Log "Start install-prerequisites, deploy=$script:DeployScriptRoot"

$layout = Test-ProjectLayout
if (-not $layout.Ok) {
    Write-Fail "Invalid project layout (drive letter C/D does not matter):"
    $layout.Errors | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Expected:" -ForegroundColor Yellow
    Write-Host "  D:\vue3sys\youlai-django\"
    Write-Host "  D:\vue3sys\vue3-element-admin\"
    Write-Host "  D:\vue3sys\deploy\"
    throw "Layout check failed"
}
Write-Ok "Project root: $($layout.Paths.ProjectRoot)"

function Show-PrerequisiteReport {
    param($Status)
    Write-Step "System"
    Report-Line "Administrator" $Status.IsAdmin "run bat as Administrator"
    Report-Line "winget" $Status.WingetAvailable "install App Installer or manual download"

    Write-Step "Required"
    Report-Line "Python 3.10-3.14" $Status.PythonOk
    Report-Line "Node.js" $Status.NodeOk
    Report-Line "pnpm" $Status.PnpmOk "npm install -g pnpm after Node"
    Report-Line "MySQL client" $Status.MySqlClientOk
    if ($Status.MySqlPortOk) {
        Report-Line "MySQL port 3306" $true
    } else {
        $hint = "service: $($Status.MySqlService.ServiceName) $($Status.MySqlService.Status)"
        Report-Line "MySQL port 3306" $false $hint
    }

    Write-Step "Bundled"
    Report-Line "Redis folder" $Status.RedisBundledOk "include Redis in project zip"
}

function Report-Line {
    param([string]$Name, [bool]$Ok, [string]$Hint = '')
    if ($Ok) {
        Write-Ok $Name
    } else {
        $msg = if ($Hint) { "$Name - $Hint" } else { $Name }
        Write-Fail $msg
    }
}

function Install-WingetPackage {
    param(
        [string]$Id,
        [string]$Name,
        [string]$ManualUrl
    )
    Write-Step "Install $Name (winget: $Id)"
    if (-not (Test-WingetAvailable)) {
        Write-Fail "winget not available. Manual: $ManualUrl"
        return $false
    }
    & winget install --id $Id -e --accept-package-agreements --accept-source-agreements --scope machine
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) {
        Write-Warn "winget exit code $LASTEXITCODE. Manual: $ManualUrl"
        return $false
    }
    Refresh-SessionPath
    Write-Ok "$Name installed or already present"
    return $true
}

function Install-PnpmGlobal {
    if (Test-CommandExists 'pnpm') {
        Write-Ok "pnpm OK"
        return $true
    }
    if (-not (Test-CommandExists 'npm')) {
        Write-Fail "npm not found"
        return $false
    }
    Write-Step "Install pnpm"
    & npm install -g pnpm
    Refresh-SessionPath
    if (Test-CommandExists 'pnpm') {
        Write-Ok "pnpm installed"
        return $true
    }
    Write-Fail "pnpm install failed. Run: npm install -g pnpm"
    return $false
}

function Show-ManualInstallGuide {
    param($Config)
    Write-Host ""
    Write-Host "======== Manual install ========" -ForegroundColor Yellow
    Write-Host "Python : $($Config.winget.python.manualUrl)"
    Write-Host "  -> check Add python.exe to PATH"
    Write-Host "Node.js: $($Config.winget.nodejs.manualUrl)"
    Write-Host "MySQL  : $($Config.winget.mysql.manualUrl)"
    Write-Host "  -> set root password for configure.ps1"
    Write-Host "pnpm   : npm install -g pnpm"
    Write-Host "================================"
}

function Request-InstallConfirm {
    param([string]$Name)
    if ($InstallAll) { return $true }
    $answer = Read-Host "Install $Name ? (Y/n)"
    return ($answer -ne 'n' -and $answer -ne 'N')
}

if (-not (Test-IsAdmin) -and -not $CheckOnly) {
    Write-Warn "Not running as Administrator. winget install may fail."
    Write-Host "Tip: right-click bat -> Run as administrator" -ForegroundColor Yellow
    if (-not $InstallAll) {
        $cont = Read-Host "Continue anyway? (y/N)"
        if ($cont -ne 'y' -and $cont -ne 'Y') { exit 1 }
    }
}

$status = Get-PrerequisiteStatus
Show-PrerequisiteReport -Status $status

if ($CheckOnly) {
    $missing = -not ($status.PythonOk -and $status.NodeOk -and $status.MySqlClientOk -and $status.MySqlPortOk)
    if ($missing) {
        Write-Warn "Missing components. Run install-prerequisites.ps1 without -CheckOnly"
        exit 1
    }
    Write-Ok "Prerequisites OK"
    exit 0
}

$config = $status.Config

if (-not $status.PythonOk) {
    if (Request-InstallConfirm 'Python 3.12') {
        $null = Install-WingetPackage -Id $config.winget.python.id -Name $config.winget.python.name -ManualUrl $config.winget.python.manualUrl
    }
}

Refresh-SessionPath
$status = Get-PrerequisiteStatus

if (-not $status.NodeOk) {
    if (Request-InstallConfirm 'Node.js LTS') {
        $null = Install-WingetPackage -Id $config.winget.nodejs.id -Name $config.winget.nodejs.name -ManualUrl $config.winget.nodejs.manualUrl
    }
}

Refresh-SessionPath

if (-not $SkipVcRedist) {
    if (Request-InstallConfirm 'VC++ Redistributable') {
        $null = Install-WingetPackage -Id $config.winget.vcredist.id -Name $config.winget.vcredist.name -ManualUrl $config.winget.vcredist.manualUrl
    }
}

if (-not $SkipMySQL) {
    $status = Get-PrerequisiteStatus
    if (-not $status.MySqlClientOk -or -not $status.MySqlPortOk) {
        if (Request-InstallConfirm 'MySQL Server 8') {
            Write-Warn "MySQL may show GUI installer. Set root password."
            $null = Install-WingetPackage -Id $config.winget.mysql.id -Name $config.winget.mysql.name -ManualUrl $config.winget.mysql.manualUrl
            Start-Sleep -Seconds 5
            Refresh-SessionPath
            Start-MySqlServiceIfNeeded -Config $config | Out-Null
        }
    }
}

Refresh-SessionPath
$mysqlBin = Find-MySqlBinDirectory -Config $config
if ($mysqlBin) {
    Add-PathToSession $mysqlBin
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($userPath -notlike "*$mysqlBin*") {
        [Environment]::SetEnvironmentVariable('Path', "$mysqlBin;$userPath", 'User')
        Write-Ok "Added MySQL bin to PATH: $mysqlBin"
    }
}

Install-PnpmGlobal | Out-Null
Start-MySqlServiceIfNeeded -Config $config | Out-Null

Write-Step "Re-check"
$status = Get-PrerequisiteStatus
Show-PrerequisiteReport -Status $status

$ready = $status.PythonOk -and $status.NodeOk -and $status.PnpmOk -and $status.MySqlClientOk
if (-not $ready) {
    Show-ManualInstallGuide -Config $config
    Write-Fail "Some components missing. Install manually and re-run."
    exit 1
}

if (-not $status.MySqlPortOk) {
    Write-Warn "MySQL client found but port 3306 not listening"
    Write-Host "Start MySQL80 in services.msc, then re-open terminal" -ForegroundColor Yellow
}

Write-Ok "Done. Next: configure.ps1 -> install-deps.ps1 -> import-database.ps1"
Write-Log "Finished OK"
exit 0
