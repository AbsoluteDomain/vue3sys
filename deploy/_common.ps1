# vue3sys deploy common helpers (ASCII-only, PowerShell 5.1+)

if ($PSScriptRoot) {
    $script:DeployScriptRoot = $PSScriptRoot
} elseif ($MyInvocation.MyCommand.Path) {
    $script:DeployScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    $script:DeployScriptRoot = (Get-Location).Path
}

function Get-DeployScriptRoot {
    return $script:DeployScriptRoot
}

function Get-ProjectPaths {
    $deployRoot = $script:DeployScriptRoot
    if (-not (Test-Path $deployRoot)) {
        throw "Deploy folder not found: $deployRoot"
    }
    $projectRoot = Split-Path -Parent $deployRoot
    [PSCustomObject]@{
        DeployRoot   = $deployRoot
        ProjectRoot  = $projectRoot
        BackendRoot  = Join-Path $projectRoot 'youlai-django'
        FrontendRoot = Join-Path $projectRoot 'vue3-element-admin'
        RedisRoot    = Join-Path $projectRoot 'Redis'
        VenvPython   = Join-Path $projectRoot 'youlai-django\venv\Scripts\python.exe'
        VenvPip      = Join-Path $projectRoot 'youlai-django\venv\Scripts\pip.exe'
        BackendEnv   = Join-Path $projectRoot 'youlai-django\.env'
        LogDir       = Join-Path $deployRoot 'logs'
    }
}

function Initialize-LogDir {
    param([string]$LogDir)
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[!!] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[XX] $Message" -ForegroundColor Red
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-TcpPort {
    param(
        [string]$HostName = '127.0.0.1',
        [int]$Port,
        [int]$TimeoutMs = 2000
    )
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        $success = $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if ($success -and $client.Connected) {
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    } catch {
        return $false
    }
}

function Read-EnvValue {
    param(
        [string]$Prompt,
        [string]$Default = ''
    )
    if ($Default) {
        $inputVal = Read-Host "$Prompt [$Default]"
        if ([string]::IsNullOrWhiteSpace($inputVal)) { return $Default }
        return $inputVal.Trim()
    }
    return (Read-Host $Prompt).Trim()
}

function New-RandomSecret {
    param([int]$Length = 48)
    $bytes = New-Object byte[] $Length
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes) -replace '[^a-zA-Z0-9]', 'x'
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal $identity
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-WingetAvailable {
    if (-not (Test-CommandExists 'winget')) { return $false }
    try {
        $null = & winget --version 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Refresh-SessionPath {
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath"
}

function Get-PrerequisitesConfig {
    $configPath = Join-Path $script:DeployScriptRoot 'prerequisites-config.json'
    if (-not (Test-Path $configPath)) {
        throw "Missing prerequisites-config.json at: $configPath"
    }
    try {
        return Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        throw "Invalid prerequisites-config.json: $($_.Exception.Message)"
    }
}

function Test-ProjectLayout {
    $paths = Get-ProjectPaths
    $errors = @()
    if (-not (Test-Path $paths.BackendRoot)) {
        $errors += "Missing backend: $($paths.BackendRoot)"
    }
    if (-not (Test-Path $paths.FrontendRoot)) {
        $errors += "Missing frontend: $($paths.FrontendRoot)"
    }
    if (-not (Test-Path (Join-Path $script:DeployScriptRoot 'install-prerequisites.ps1'))) {
        $errors += "Incomplete deploy folder. Extract full vue3sys zip."
    }
    [PSCustomObject]@{
        Ok     = ($errors.Count -eq 0)
        Errors = $errors
        Paths  = $paths
    }
}

function Test-PythonVersionOk {
    param($Config)
    if (-not (Test-CommandExists 'python')) { return $false }
    $verText = (& python --version 2>&1) -join ' '
    if ($verText -notmatch 'Python (\d+)\.(\d+)') { return $false }
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    $min = $Config.pythonMinVersion
    $max = $Config.pythonMaxVersion
    $minVal = $min[0] * 100 + $min[1]
    $maxVal = $max[0] * 100 + $max[1]
    $curVal = $major * 100 + $minor
    return ($curVal -ge $minVal -and $curVal -le $maxVal)
}

function Find-MySqlBinFromService {
    param($Config)
    foreach ($name in $Config.winget.mysql.serviceNames) {
        $svc = Get-CimInstance Win32_Service -Filter "Name='$name'" -ErrorAction SilentlyContinue
        if (-not $svc -or -not $svc.PathName) { continue }
        $pathName = $svc.PathName.Trim()
        $binDir = $null
        if ($pathName -match '^"([^"]+\\bin)\\mysqld\.exe"') {
            $binDir = $Matches[1]
        } elseif ($pathName -match '^([^\s]+\\bin)\\mysqld\.exe') {
            $binDir = $Matches[1]
        }
        if ($binDir -and (Test-Path (Join-Path $binDir 'mysql.exe'))) {
            return $binDir
        }
    }
    return $null
}

function Find-MySqlBinDirectory {
    param($Config)
    if (Test-CommandExists 'mysql') {
        return (Split-Path (Get-Command mysql).Source -Parent)
    }
    $fromService = Find-MySqlBinFromService -Config $Config
    if ($fromService) { return $fromService }
    foreach ($path in $Config.mysqlBinPaths) {
        if (Test-Path (Join-Path $path 'mysql.exe')) {
            return $path
        }
    }
    $pf86 = ${env:ProgramFiles(x86)}
    $programFiles = @(${env:ProgramFiles})
    if ($pf86) { $programFiles += $pf86 }
    Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.Root 'Program Files' } |
        Where-Object { $_ -and (Test-Path $_) } |
        ForEach-Object { if ($programFiles -notcontains $_) { $programFiles += $_ } }
    foreach ($root in $programFiles) {
        $mysqlRoot = Join-Path $root 'MySQL'
        if (-not (Test-Path $mysqlRoot)) { continue }
        $bins = Get-ChildItem -Path $mysqlRoot -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName 'bin' } |
            Where-Object { Test-Path (Join-Path $_ 'mysql.exe') }
        if ($bins) { return $bins[0] }
    }
    return $null
}

function Add-PathToSession {
    param([string]$Directory)
    if ([string]::IsNullOrWhiteSpace($Directory)) { return }
    if ($env:Path -notlike "*$Directory*") {
        $env:Path = "$Directory;$env:Path"
    }
}

function Test-MySqlServiceRunning {
    param($Config)
    foreach ($name in $Config.winget.mysql.serviceNames) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -eq 'Running') {
            return [PSCustomObject]@{ Ok = $true; ServiceName = $name; Status = $svc.Status }
        }
        if ($svc) {
            return [PSCustomObject]@{ Ok = $false; ServiceName = $name; Status = $svc.Status }
        }
    }
    return [PSCustomObject]@{ Ok = $false; ServiceName = ''; Status = 'NotFound' }
}

function Start-MySqlServiceIfNeeded {
    param($Config)
    foreach ($name in $Config.winget.mysql.serviceNames) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if (-not $svc) { continue }
        if ($svc.Status -ne 'Running') {
            try {
                Start-Service -Name $name
                Write-Ok "MySQL service started: $name"
            } catch {
                Write-Warn "Cannot start MySQL ${name}: $($_.Exception.Message)"
            }
        } else {
            Write-Ok "MySQL service running: $name"
        }
        return $true
    }
    return $false
}

function Get-PrerequisiteStatus {
    $config = Get-PrerequisitesConfig
    Refresh-SessionPath
    $mysqlBin = Find-MySqlBinDirectory -Config $config
    if ($mysqlBin) { Add-PathToSession $mysqlBin }

    [PSCustomObject]@{
        Config          = $config
        IsAdmin         = Test-IsAdmin
        WingetAvailable = Test-WingetAvailable
        PythonOk        = Test-PythonVersionOk -Config $config
        NodeOk          = Test-CommandExists 'node'
        PnpmOk          = Test-CommandExists 'pnpm'
        MySqlClientOk   = [bool]$mysqlBin -or (Test-CommandExists 'mysql')
        MySqlPortOk     = Test-TcpPort -Port 3306
        MySqlService    = Test-MySqlServiceRunning -Config $config
        RedisBundledOk  = Test-Path (Join-Path (Split-Path $script:DeployScriptRoot -Parent) 'Redis\redis-server.exe')
    }
}
