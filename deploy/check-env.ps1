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
    Report "Administrator" $pre.IsAdmin "need for install" -IsWarning:$(-not $pre.IsAdmin)
    Report "winget" $pre.WingetAvailable "optional" -IsWarning:$(-not $pre.WingetAvailable)
    Report "Python" $pre.PythonOk "run install-prerequisites"
    Report "Node.js" $pre.NodeOk "install Node.js manually"
    Report "pnpm" $pre.PnpmOk "npm install -g pnpm" -IsWarning:$(-not $pre.PnpmOk)
    Report "MySQL client" $pre.MySqlClientOk "install MySQL"
    Report "MySQL port 3306" $pre.MySqlPortOk "start MySQL84 service"
} catch {
    Report "Prerequisite check" $false $_.Exception.Message
}

Write-Step "Project paths"
Report "Project root" (Test-Path $paths.ProjectRoot) $paths.ProjectRoot
Report "Backend" (Test-Path $paths.BackendRoot) $paths.BackendRoot
Report "Frontend" (Test-Path $paths.FrontendRoot) $paths.FrontendRoot
Report "Redis folder" (Test-Path $paths.RedisRoot) $paths.RedisRoot -IsWarning

Write-Step "Config files"
Report "Backend .env" (Test-Path $paths.BackendEnv) $(if (Test-Path $paths.BackendEnv) { 'OK' } else { 'run configure.ps1' })
$feEnv = Join-Path $paths.FrontendRoot '.env.development'
Report "Frontend .env" (Test-Path $feEnv) $(if (Test-Path $feEnv) { 'OK' } else { 'run configure.ps1' })

$sqlFile = Join-Path $paths.ProjectRoot 'youlai_admin_django.sql'
Report "SQL backup" (Test-Path $sqlFile) $(if (Test-Path $sqlFile) { 'OK' } else { 'optional' }) -IsWarning

Write-Step "venv"
Report "Python venv" (Test-Path $paths.VenvPython) $(if (Test-Path $paths.VenvPython) { 'OK' } else { 'run install-deps.ps1' })

Write-Step "Ports"
foreach ($p in @(
    @{ Name = 'MySQL'; Port = 3306 },
    @{ Name = 'Redis'; Port = 6379 },
    @{ Name = 'Django'; Port = 8000 },
    @{ Name = 'Frontend'; Port = 3000 }
)) {
    $open = Test-TcpPort -Port $p.Port
    Report $p.Name $open "port $($p.Port)" -IsWarning:$(-not $open)
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
    Report "django check" $ok $(if ($ok) { 'OK' } else { $checkText })
} else {
    Report "django check" $false "skip" -IsWarning
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
