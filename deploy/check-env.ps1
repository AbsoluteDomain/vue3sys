# Environment check (ASCII-only)

param(
    [switch]$Quiet
)

$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths
Initialize-LogDir $paths.LogDir

$issues = @()
$warnings = @()
$passed = 0

function Report {
    param([string]$Name, [bool]$Ok, [string]$Detail = '', [switch]$IsWarning)
    if ($Ok) {
        $script:passed++
        if (-not $Quiet) { Write-Ok "$Name $Detail" }
    } elseif ($IsWarning) {
        $script:warnings += "$Name $Detail"
        if (-not $Quiet) { Write-Warn "$Name $Detail" }
    } else {
        $script:issues += "$Name $Detail"
        if (-not $Quiet) { Write-Fail "$Name $Detail" }
    }
}

Write-Step "Prerequisites"
try {
    $pre = Get-PrerequisiteStatus
    $rp = $pre.ResolvedPaths

    function ResolveLine {
        param([string]$Name, [bool]$Ok, [string]$Hint, [string]$ResolvedDir = '')
        if ($Ok -and -not [string]::IsNullOrWhiteSpace($ResolvedDir)) {
            # Detected = show the real install path so customer can verify
            $detail = "-> $ResolvedDir"
            Report $Name $true $detail
        } elseif ($Ok) {
            Report $Name $true "(found in PATH)"
        } else {
            if (-not [string]::IsNullOrWhiteSpace($ResolvedDir)) {
                $detail = "dir exists: $ResolvedDir  (but not in PATH; deploy will inject it automatically)"
                Report $Name $false $detail -IsWarning
            } else {
                Report $Name $false $Hint
            }
        }
    }

    if ($pre.IsAdmin) {
        Report "Administrator" $true
    } else {
        Report "Administrator" $false "needed for winget prerequisite installs" -IsWarning
    }
    if ($pre.WingetAvailable) {
        Report "winget" $true
    } else {
        Report "winget" $false "optional, use manual install links if prerequisites missing" -IsWarning
    }

    ResolveLine -Name "Python"  -Ok $pre.PythonOk  -Hint "run install-prerequisites (Admin) or manual install Python 3.10-3.14" -ResolvedDir $rp.PythonBinDir
    ResolveLine -Name "Node.js" -Ok $pre.NodeOk    -Hint "install Node.js 20.19+ manually or reboot once"                         -ResolvedDir $rp.NodeBinDir
    ResolveLine -Name "MySQL client" -Ok $pre.MySqlClientOk -Hint "install MySQL Server 8 (run MySQL installer) then re-open bat"  -ResolvedDir $rp.MySqlBinDir

    if ($pre.PnpmOk) {
        if (-not [string]::IsNullOrWhiteSpace($rp.PnpmBinDir)) {
            Report "pnpm" $true ("-> " + $rp.PnpmBinDir)
        } else {
            Report "pnpm" $true
        }
    } else {
        $detail = "run: npm install -g pnpm"
        if (-not [string]::IsNullOrWhiteSpace($rp.PnpmBinDir)) {
            $detail = "dir exists: $($rp.PnpmBinDir) (deploy will inject; auto run npm i -g pnpm next)"
            Report "pnpm" $false $detail -IsWarning
        } else {
            Report "pnpm" $false $detail -IsWarning
        }
    }

    if (Test-CommandExists 'uv') {
        $uvVer = (& uv --version 2>$null).Trim()
        Write-Host "  [OK] uv              $uvVer (faster venv/pip)" -ForegroundColor Green
    } else {
        Write-Host "  [..] uv              pip install uv (optional 5-10x faster)" -ForegroundColor Gray
    }
    Report "MySQL port 3306" $pre.MySqlPortOk "start MySQL80 / MySQL84 in services.msc"
} catch {
    Report "Prerequisite check" $false $_.Exception.Message
}

Write-Step "Project paths"
Report "Project root" (Test-Path $paths.ProjectRoot) $paths.ProjectRoot
Report "Backend" (Test-Path $paths.BackendRoot) $paths.BackendRoot
Report "Frontend" (Test-Path $paths.FrontendRoot) $paths.FrontendRoot
if (Test-Path $paths.RedisRoot) {
    Report "Redis folder" $true $paths.RedisRoot
} else {
    Report "Redis folder" $false $paths.RedisRoot -IsWarning
}

Write-Step "Config files"
if (Test-Path $paths.BackendEnv) {
    Report "Backend .env" $true "OK"
} else {
    Report "Backend .env" $false "run configure.ps1 first"
}
$feEnv = Join-Path $paths.FrontendRoot '.env.development'
if (Test-Path $feEnv) {
    Report "Frontend .env" $true "OK"
} else {
    Report "Frontend .env" $false "run configure.ps1 first"
}

$sqlFile = Join-Path $paths.ProjectRoot 'youlai_admin_django.sql'
if (Test-Path $sqlFile) {
    Report "SQL backup" $true "OK"
} else {
    Report "SQL backup" $false "optional (full deploy will fail without it)" -IsWarning
}

Write-Step "venv"
if (Test-Path $paths.VenvPython) {
    Report "Python venv" $true "OK"
} else {
    Report "Python venv" $false "run install-deps.ps1"
}

Write-Step "Ports"
foreach ($p in @(
    @{ Name = 'MySQL'; Port = 3306 },
    @{ Name = 'Redis'; Port = 6379 },
    @{ Name = 'Django'; Port = 8000 },
    @{ Name = 'Frontend'; Port = 3000 }
)) {
    $open = Test-TcpPort -Port $p.Port
    if ($open) {
        Report $p.Name $true "port $($p.Port)"
    } else {
        Report $p.Name $false "port $($p.Port) not listening (OK if service not started yet)" -IsWarning
    }
}

Write-Step "django check"
if (Test-Path $paths.VenvPython) {
    Push-Location $paths.BackendRoot
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    $checkLines = & $paths.VenvPython manage.py check 2>&1
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    Pop-Location
    $checkText = ($checkLines | Out-String).Trim()
    $ok = ($exitCode -eq 0) -and (
        $checkText -match 'System check identified no issues' -or
        ($checkText -notmatch 'Traceback|Error:|CommandError' -and $checkText -ne '')
    )
    if ($ok) {
        Report "django check" $true "OK"
    } else {
        # Trim long error to one line
        $oneLine = ($checkText -split "`r?`n" | Select-Object -First 3) -join ' | '
        if ($oneLine.Length -gt 300) { $oneLine = $oneLine.Substring(0, 300) + '...' }
        Report "django check" $false $oneLine
    }
} else {
    Report "django check" $false "skip (no venv yet)" -IsWarning
}

Write-Step "Summary"
Write-Host "Pass: $passed | Warn: $($warnings.Count) | Fail: $($issues.Count)"

if ($issues.Count -gt 0) {
    Write-Fail "Issues:"
    $issues | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
}

if ($issues.Count -eq 0) {
    Write-Ok "Check passed"
    exit 0
}
exit 1
