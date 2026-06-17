# vue3sys deploy diagnose (standalone, ASCII-only)

param()

$ErrorActionPreference = 'Continue'
$deployDir = $PSScriptRoot
if (-not $deployDir) {
    $deployDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
$projectRoot = Split-Path $deployDir -Parent

$logDir = Join-Path $deployDir 'logs'
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$logFile = Join-Path $logDir ("diagnose_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

function Log-Line {
    param([string]$Text)
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Text
    Add-Content -Path $logFile -Value $line -Encoding UTF8
    Write-Host $Text
}

function Log-OkFail {
    param([string]$Name, [bool]$Ok, [string]$FailHint)
    if ($Ok) {
        Log-Line "[OK] $Name"
    } elseif ($FailHint) {
        Log-Line "[FAIL] $Name - $FailHint"
    } else {
        Log-Line "[FAIL] $Name"
    }
}

function Test-IsAdminLocal {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal $identity
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-WingetLocal {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { return $false }
    try {
        $null = & winget --version 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Test-PythonLocal {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { return $false }
    $verText = (& python --version 2>&1) -join ' '
    if ($verText -notmatch 'Python (\d+)\.(\d+)') { return $false }
    $cur = [int]$Matches[1] * 100 + [int]$Matches[2]
    return ($cur -ge 310 -and $cur -le 314)
}

function Test-TcpPortLocal {
    param([int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(2000, $false)
        if ($ok -and $client.Connected) {
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    } catch {
        return $false
    }
}

function Get-ProjectLayoutLocal {
    $errors = @()
    $backend = Join-Path $projectRoot 'youlai-django'
    $frontend = Join-Path $projectRoot 'vue3-element-admin'
    if (-not (Test-Path $backend)) { $errors += "Missing: $backend" }
    if (-not (Test-Path $frontend)) { $errors += "Missing: $frontend" }
    [PSCustomObject]@{
        Ok = ($errors.Count -eq 0)
        Errors = $errors
    }
}

try {
    Log-Line "======== vue3sys deploy diagnose ========"
    Log-Line "Deploy dir  : $deployDir"
    Log-Line "Project root: $projectRoot"

    $commonPath = Join-Path $deployDir '_common.ps1'
    $useCommon = $false
    if (Test-Path $commonPath) {
        try {
            . $commonPath
            $script:DeployScriptRoot = $deployDir
            if (Get-Command Test-ProjectLayout -ErrorAction SilentlyContinue) {
                $useCommon = $true
                Log-Line "[OK] Loaded _common.ps1"
            } else {
                Log-Line "[WARN] _common.ps1 is old version, using built-in checks"
            }
        } catch {
            Log-Line "[WARN] _common.ps1 load failed: $($_.Exception.Message)"
        }
    } else {
        Log-Line "[FAIL] Missing _common.ps1"
    }

    if ($useCommon) {
        $layout = Test-ProjectLayout
    } else {
        $layout = Get-ProjectLayoutLocal
    }
    if ($layout.Ok) {
        Log-Line "[OK] Project layout"
    } else {
        Log-Line "[FAIL] Project layout:"
        $layout.Errors | ForEach-Object { Log-Line "       $_" }
    }

    Log-Line ""
    Log-Line "--- Required files ---"
    @(
        'install-prerequisites.ps1',
        '_common.ps1',
        'prerequisites-config.json',
        'diagnose.ps1'
    ) | ForEach-Object {
        Log-OkFail $_ (Test-Path (Join-Path $deployDir $_)) "missing"
    }

    Log-Line ""
    Log-Line "--- Environment ---"
    Log-OkFail "Run as Administrator" (Test-IsAdminLocal) "right-click bat -> Run as administrator"
    Log-Line "PowerShell: $($PSVersionTable.PSVersion)"
    Log-OkFail "winget" (Test-WingetLocal) "install App Installer or manual install"

    Log-Line ""
    Log-Line "--- Installed software ---"
    if ($useCommon) {
        try {
            $st = Get-PrerequisiteStatus
            Log-OkFail "Python 3.10-3.14" $st.PythonOk "not installed"
            Log-OkFail "Node.js" $st.NodeOk "not installed"
            Log-OkFail "pnpm" $st.PnpmOk "npm install -g pnpm"
            Log-OkFail "MySQL client" $st.MySqlClientOk "install MySQL Server 8"
            Log-OkFail "MySQL port 3306" $st.MySqlPortOk "start MySQL80 service"
            Log-OkFail "Redis (bundled)" $st.RedisBundledOk "include Redis folder"
        } catch {
            Log-Line "[FAIL] Software check: $($_.Exception.Message)"
        }
    } else {
        Log-OkFail "Python 3.10-3.14" (Test-PythonLocal) "not installed"
        Log-OkFail "Node.js" ([bool](Get-Command node -ErrorAction SilentlyContinue)) "not installed"
        Log-OkFail "pnpm" ([bool](Get-Command pnpm -ErrorAction SilentlyContinue)) "npm install -g pnpm"
        Log-OkFail "MySQL port 3306" (Test-TcpPortLocal -Port 3306) "install and start MySQL80"
        Log-OkFail "Redis (bundled)" (Test-Path (Join-Path $projectRoot 'Redis\redis-server.exe')) "include Redis folder"
    }

    Log-Line ""
    Log-Line "Log saved: $logFile"
    Log-Line "Next: copy ALL deploy files, then run install-prerequisites as Administrator"
    exit 0
} catch {
    Log-Line "[FAIL] Diagnose error: $($_.Exception.Message)"
    Log-Line $_.ScriptStackTrace
    exit 1
}
