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
    # Read fresh PATH from registry (Machine + User) and overwrite in-process $env:Path.
    # Critical when prerequisites were JUST INSTALLED in the same bat/session: new programs
    # added their install paths to registry Environment, but this PowerShell session's
    # $env:Path still holds the snapshot taken when cmd.exe/explorer launched the bat.
    # Without Refresh-SessionPath, Test-CommandExists would report "not found" even
    # though the software is already installed.
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath    = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ([string]::IsNullOrWhiteSpace($machinePath)) { $machinePath = '' }
    if ([string]::IsNullOrWhiteSpace($userPath))    { $userPath = '' }
    if ($machinePath -and $userPath) {
        $env:Path = "$machinePath;$userPath"
    } elseif ($machinePath) {
        $env:Path = $machinePath
    } elseif ($userPath) {
        $env:Path = $userPath
    }
    # Remove duplicated semicolons
    while ($env:Path -match ';;') { $env:Path = $env:Path -replace ';;',';' }
}

function Broadcast-EnvironmentChange {
    # Notify all top-level windows (including Explorer/Desktop) that Environment
    # variables have changed. New CMD/PowerShell windows opened AFTER this call
    # will see updated PATH. Current windows must still call Refresh-SessionPath.
    #
    # Uses the classic SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE,
    # 0, "Environment", SMTO_ABORTIFHUNG, 5000, ...) Win32 call via C# reflection.
    try {
        Add-Type -Namespace Win32 -Name NativeMethods -MemberDefinition @'
using System;
using System.Runtime.InteropServices;
public static class NativeEnvironment {
    private const int HWND_BROADCAST = 0xFFFF;
    private const uint WM_SETTINGCHANGE = 0x001A;
    private const uint SMTO_ABORTIFHUNG = 0x0002;

    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    private static extern IntPtr SendMessageTimeout(
        IntPtr hWnd,
        uint Msg,
        UIntPtr wParam,
        string lParam,
        uint fuFlags,
        uint uTimeout,
        out UIntPtr lpdwResult);

    public static int BroadcastEnvironmentChange() {
        UIntPtr result;
        IntPtr ret = SendMessageTimeout(
            (IntPtr)HWND_BROADCAST,
            WM_SETTINGCHANGE,
            UIntPtr.Zero,
            "Environment",
            SMTO_ABORTIFHUNG,
            5000,
            out result);
        return (int)ret; // non-zero = success
    }
}
'@ -ErrorAction Stop | Out-Null
        $null = [Win32.NativeMethods+NativeEnvironment]::BroadcastEnvironmentChange()
        return $true
    } catch {
        # This broadcast is best-effort (newly opened windows will auto pick-up).
        return $false
    }
}

function Get-RegistryValueOrDefault {
    param(
        [string[]]$Paths,
        [string]$Name,
        [string]$Default = $null
    )
    foreach ($p in $Paths) {
        try {
            $item = Get-Item -Path $p -ErrorAction Stop
            if (-not $item) { continue }
            if ($null -ne $item.GetValue($Name)) {
                return [string]$item.GetValue($Name)
            }
        } catch {
            continue
        }
    }
    return $Default
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

    # (0) Ensure registry Environment PATH is reloaded.
    # Without this, a customer that manually installed MySQL 2 minutes ago but
    # kept the same bat/cmd window open will "not have mysql in PATH" even though
    # the installer appended MySQL bin to Machine\Environment\Path.
    Refresh-SessionPath

    # (1) PATH first (already in env PATH → use it directly)
    if (Test-CommandExists 'mysql') {
        return (Split-Path (Get-Command mysql).Source -Parent)
    }

    # (2) MySQL installer stores versioned install directory in these reg keys:
    #   64-bit: HKLM:\SOFTWARE\MySQL AB\MySQL Server X.Y   InstallLocation=...\MySQL Server X.Y\
    #   32-bit: HKLM:\SOFTWARE\WOW6432Node\MySQL AB\MySQL Server X.Y
    $regRoots = @(
        'HKLM:\SOFTWARE\MySQL AB',
        'HKLM:\SOFTWARE\WOW6432Node\MySQL AB',
        'HKCU:\SOFTWARE\MySQL AB'
    )
    foreach ($regBase in $regRoots) {
        if (-not (Test-Path $regBase)) { continue }
        try {
            $subKeys = Get-ChildItem -Path $regBase -ErrorAction Stop
            foreach ($sk in $subKeys) {
                if ($sk.Name -notmatch 'MySQL Server') { continue }
                $loc = $sk.GetValue('InstallLocation')
                if (-not $loc) { continue }
                $binDir = Join-Path $loc 'bin'
                if (Test-Path (Join-Path $binDir 'mysql.exe')) { return $binDir }
                if (Test-Path (Join-Path $loc 'mysql.exe'))    { return $loc.TrimEnd('\') }
            }
        } catch {
            continue
        }
    }

    # (3) From running / registered service ImagePath (handles non-standard installs
    #     where user picked a custom folder; works even if PATH was never updated)
    $fromService = Find-MySqlBinFromService -Config $Config
    if ($fromService) { return $fromService }

    # (4) Config's manual list
    if ($Config -and $Config.mysqlBinPaths) {
        foreach ($path in $Config.mysqlBinPaths) {
            if (Test-Path (Join-Path $path 'mysql.exe')) {
                return $path
            }
        }
    }

    # (5) Scan %ProgramFiles%\MySQL\...\bin & all drives
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

    # (6) XAMPP / WAMP common locations (very common on Chinese customer machines)
    foreach ($alt in @('C:\xampp\mysql\bin','D:\xampp\mysql\bin','C:\wamp64\bin\mysql\bin','D:\wamp64\bin\mysql\bin')) {
        if (Test-Path (Join-Path $alt 'mysql.exe')) { return $alt }
    }

    return $null
}

function Find-NodeBinDirectory {
    # Aggressively try to find node.exe even if it's not in PATH yet.
    # Returns directory that contains node.exe (and typically npm.cmd as well).
    # Typical cases where we need this:
    #   1. Customer just installed Node.js in the same bat → PATH snapshot stale.
    #   2. Node installed per-user (not added to Machine PATH) and HKCU PATH not yet
    #      broadcast to the running bat.
    #   3. Customer used NVM-windows and forgot to 'nvm use', or NVM symlink missing.
    #   4. Installer extracted node.exe somewhere unusual (portable mode).

    # (0) Fresh PATH reload (handles 90% of "just installed" cases)
    Refresh-SessionPath

    # (1) In-process PATH
    if (Test-CommandExists 'node') {
        return (Split-Path (Get-Command node).Source -Parent)
    }

    # (2) Official Node.js MSI installers write InstallPath to these locations
    $nodeRegKeys = @(
        'HKLM:\SOFTWARE\Node.js',
        'HKLM:\SOFTWARE\WOW6432Node\Node.js',
        'HKCU:\SOFTWARE\Node.js'
    )
    foreach ($rk in $nodeRegKeys) {
        if (-not (Test-Path $rk)) { continue }
        try {
            $path = (Get-Item $rk -ErrorAction Stop).GetValue('InstallPath')
            if ($path -and (Test-Path (Join-Path $path 'node.exe'))) { return $path.TrimEnd('\') }
        } catch {}
    }

    # (3) NVM for Windows: NVM_HOME + its symlink.  Respect the `current` symlink.
    $nvmHome = Get-RegistryValueOrDefault `
        -Paths @('HKLM:\SOFTWARE\OpenJSFoundation\NVM for Windows','HKCU:\SOFTWARE\OpenJSFoundation\NVM for Windows','HKLM:\SOFTWARE\nvm-windows','HKCU:\SOFTWARE\nvm-windows') `
        -Name 'InstallPath'
    if ([string]::IsNullOrWhiteSpace($nvmHome) -and -not [string]::IsNullOrWhiteSpace($env:NVM_HOME)) {
        $nvmHome = $env:NVM_HOME
    }
    if ($nvmHome -and (Test-Path $nvmHome)) {
        try {
            # NVM sets a symlink like C:\Program Files\nodejs -> versioned dir in NVM_HOME.
            # Also check env:
            $sym = Get-RegistryValueOrDefault `
                -Paths @('HKLM:\SOFTWARE\OpenJSFoundation\NVM for Windows','HKCU:\SOFTWARE\OpenJSFoundation\NVM for Windows','HKLM:\SOFTWARE\nvm-windows','HKCU:\SOFTWARE\nvm-windows') `
                -Name 'Symlink'
            if (-not [string]::IsNullOrWhiteSpace($sym) -and (Test-Path $sym)) {
                $nodeExeInSym = Join-Path $sym 'node.exe'
                if (Test-Path $nodeExeInSym) { return $sym.TrimEnd('\') }
            }
            # No symlink value, but nodejs folder in NVM_HOME
            $installed = Get-ChildItem -Path $nvmHome -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^v?\d+\.\d+\.\d+$' } |
                Sort-Object Name -Descending
            foreach ($vDir in $installed) {
                $bin = Join-Path $vDir.FullName 'node.exe'
                if (Test-Path $bin) { return $vDir.FullName }
            }
        } catch {}
    }

    # (4) Standard install directories
    $standard = @()
    if ($env:ProgramFiles) { $standard += (Join-Path $env:ProgramFiles 'nodejs') }
    $pf86 = ${env:ProgramFiles(x86)}
    if ($pf86) { $standard += (Join-Path $pf86 'nodejs') }
    $standard += "$env:APPDATA\npm"
    $standard += "$env:LOCALAPPDATA\nodejs"
    $standard += "$env:USERPROFILE\nodejs"
    # D:\ drive portable installs are common on Chinese customer PCs
    Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | ForEach-Object {
        $standard += (Join-Path $_.Root 'nodejs')
    }
    foreach ($s in $standard) {
        if ($s -and (Test-Path (Join-Path $s 'node.exe'))) { return $s.TrimEnd('\') }
    }

    # (5) Where.exe fallback (searches PATH + app paths via Windows Installer).
    try {
        $where = & where.exe node 2>$null
        if ($where -and $where -match '^(.*[\\/])node\.exe$') {
            $candidate = $Matches[1].TrimEnd('\','/')
            if (Test-Path (Join-Path $candidate 'node.exe')) { return $candidate }
        }
    } catch {}

    return $null
}

function Find-PythonDirectory {
    # Similar to Node.js: try to find python.exe that customer installed but isn't
    # in the current session's PATH (common when installer ran 1 min ago and bat is
    # still running).
    #
    # IMPORTANT: Microsoft ships `python.exe` / `python3.exe` STUBS under
    #   %LOCALAPPDATA%\Microsoft\WindowsApps\
    # They are ~0-byte reparse points that open the Microsoft Store when run.
    # We MUST exclude these (they show up via PATH but are NOT real python).
    # A directory is considered "Python installed" only if it contains a REAL
    # python.exe > 10KB (i.e. NOT a WindowsApps stub).

    Refresh-SessionPath

    function Test-RealPythonExe {
        param([string]$PythonExe)
        if ([string]::IsNullOrWhiteSpace($PythonExe)) { return $false }
        if (-not (Test-Path $PythonExe)) { return $false }
        try {
            $fi = Get-Item $PythonExe -ErrorAction Stop
            if (-not $fi) { return $false }
            # Microsoft's WindowsApps python stubs are typically 0 bytes reparse points.
            # Real CPython python.exe is ~30-100 KB. Use > 10 KB as a strong heuristic.
            if ($fi.Length -lt 10KB) { return $false }
            # Additional sanity: try --version (store stub might print an error / open a window)
            $out = & $PythonExe --version 2>&1
            $code = $LASTEXITCODE
            if ($code -ne 0) { return $false }
            if (($out | Out-String) -notmatch 'Python \d') { return $false }
            return $true
        } catch {
            return $false
        }
    }

    # (1) PATH first — but we must filter out WindowsApps stubs.
    $pathCmds = @('python','python3')
    foreach ($pc in $pathCmds) {
        $cmd = Get-Command $pc -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        if (Test-RealPythonExe $cmd.Source) {
            return (Split-Path $cmd.Source -Parent)
        }
    }

    # (2) py launcher can launch installed python even without PATH
    if (Test-CommandExists 'py') {
        try {
            $realPath = & py -3 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $realPath -and (Test-RealPythonExe $realPath)) {
                return (Split-Path $realPath -Parent)
            }
        } catch {}
    }

    # (3) Python Software Foundation / PythonCore registry keys
    foreach ($hive in @('HKLM:\SOFTWARE\Python\PythonCore','HKCU:\SOFTWARE\Python\PythonCore','HKLM:\SOFTWARE\WOW6432Node\Python\PythonCore')) {
        if (-not (Test-Path $hive)) { continue }
        try {
            $subs = Get-ChildItem $hive -ErrorAction Stop
            foreach ($sk in $subs) {
                $ipk = Join-Path $sk.PSPath 'InstallPath'
                if (-not (Test-Path $ipk)) { continue }
                $execPath = (Get-Item $ipk -ErrorAction SilentlyContinue).GetValue('ExecutablePath')
                if ($execPath -and (Test-RealPythonExe $execPath)) {
                    return (Split-Path $execPath -Parent)
                }
                $defVal = (Get-Item $ipk -ErrorAction SilentlyContinue).GetValue('')
                $candidate = Join-Path $defVal 'python.exe'
                if ($defVal -and (Test-RealPythonExe $candidate)) {
                    return $defVal.TrimEnd('\')
                }
            }
        } catch {}
    }
    # (4) Standard dirs (filter WindowsApps out explicitly)
    $std = @()
    if ($env:LOCALAPPDATA) { $std += "$env:LOCALAPPDATA\Programs\Python" }
    if ($env:ProgramFiles) { $std += "$env:ProgramFiles\Python" }
    $pf86 = ${env:ProgramFiles(x86)}
    if ($pf86) { $std += "$pf86\Python" }
    foreach ($root in $std) {
        if (-not (Test-Path $root)) { continue }
        $hits = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName 'python.exe' } |
            Where-Object { Test-RealPythonExe $_ }
        if ($hits) { return (Split-Path $hits[0] -Parent) }
    }
    # (5) Drive-level common installs (D:\Python313 etc.) — skip WindowsApps entirely
    try {
        Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue | ForEach-Object {
            $driveRoot = $_.Root
            Get-ChildItem -Path $driveRoot -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^Python\d+' -or $_.Name -match '^python$' } |
                ForEach-Object {
                    $candidate = Join-Path $_.FullName 'python.exe'
                    if (Test-RealPythonExe $candidate) { return (Split-Path $candidate -Parent) }
                }
        } | ForEach-Object { if ($_) { return $_ } }
    } catch {}

    return $null
}

function Find-PnpmPath {
    # pnpm usually installed via npm i -g pnpm → sits next to npm.cmd, or
    # standalone pnpm installers use PNPM_HOME env var.
    if (Test-CommandExists 'pnpm') {
        return (Split-Path (Get-Command pnpm).Source -Parent)
    }
    Refresh-SessionPath
    if (Test-CommandExists 'pnpm') {
        return (Split-Path (Get-Command pnpm).Source -Parent)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:PNPM_HOME)) {
        if (Test-Path (Join-Path $env:PNPM_HOME 'pnpm.cmd')) { return $env:PNPM_HOME }
    }
    $nodeDir = Find-NodeBinDirectory
    if ($nodeDir -and (Test-Path (Join-Path $nodeDir 'pnpm.cmd'))) { return $nodeDir }
    # npm global prefix (pnpm often lives here)
    try {
        if (Test-CommandExists 'npm') {
            $globalPrefix = & npm config get prefix 2>$null
            if ($globalPrefix -and (Test-Path (Join-Path $globalPrefix 'pnpm.cmd'))) {
                return $globalPrefix.TrimEnd('\')
            }
            if ($globalPrefix -and (Test-Path (Join-Path $globalPrefix 'pnpm.exe'))) {
                return $globalPrefix.TrimEnd('\')
            }
        }
    } catch {}
    foreach ($cand in @("$env:APPDATA\npm","$env:LOCALAPPDATA\pnpm","$env:LOCALAPPDATA\npm")) {
        if (Test-Path (Join-Path $cand 'pnpm.cmd')) { return $cand }
    }
    return $null
}

function Add-PathToSession {
    param([string]$Directory)
    if ([string]::IsNullOrWhiteSpace($Directory)) { return }
    if (-not (Test-Path $Directory)) { return }
    if ($env:Path -notlike "*$Directory*") {
        $env:Path = "$Directory;$env:Path"
    }
}

function Resolve-PrerequisitePaths {
    <#
    .SYNOPSIS
      Try very hard to find Python / Node.js / pnpm / MySQL binaries that the
      customer actually installed but that "where.exe" and "Get-Command" cannot
      find because the running session has a stale PATH snapshot.

      This is the single entry point that every status-check / auto-deploy script
      should call BEFORE trying to detect availability or invoke commands.

    .OUTPUTS
      PSCustomObject with:
          PythonBinDir, NodeBinDir, PnpmBinDir, MySqlBinDir  (string, $null if not found)
          AllFound (bool)
    #>
    param()
    $config = Get-PrerequisitesConfig

    # Always refresh PATH from registry FIRST.  This alone fixes most "just
    # installed but not detected" cases caused by stale environment snapshots.
    Refresh-SessionPath

    $resolved = [ordered]@{
        PythonBinDir = $null
        NodeBinDir   = $null
        PnpmBinDir   = $null
        MySqlBinDir  = $null
    }

    # --- MySQL ---
    $mysqlBin = Find-MySqlBinDirectory -Config $config
    if ($mysqlBin) {
        Add-PathToSession $mysqlBin
        $resolved.MySqlBinDir = $mysqlBin
    }

    # --- Python ---
    $pythonBin = Find-PythonDirectory
    if ($pythonBin) {
        Add-PathToSession $pythonBin
        $scriptsDir = Join-Path $pythonBin 'Scripts'
        if (Test-Path $scriptsDir) { Add-PathToSession $scriptsDir }
        $resolved.PythonBinDir = $pythonBin
    }

    # --- Node.js (order matters: pnpm lives next to npm which lives inside node dir) ---
    $nodeBin = Find-NodeBinDirectory
    if ($nodeBin) {
        Add-PathToSession $nodeBin
        $resolved.NodeBinDir = $nodeBin
    }

    # --- pnpm ---
    $pnpmBin = Find-PnpmPath
    if ($pnpmBin) {
        Add-PathToSession $pnpmBin
        $resolved.PnpmBinDir = $pnpmBin
    }

    $allOk = $true
    foreach ($k in @('PythonBinDir','NodeBinDir','PnpmBinDir','MySqlBinDir')) {
        if ([string]::IsNullOrWhiteSpace($resolved[$k])) { $allOk = $false }
    }

    return [PSCustomObject]@{
        AllFound      = $allOk
        PythonBinDir  = $resolved.PythonBinDir
        NodeBinDir    = $resolved.NodeBinDir
        PnpmBinDir    = $resolved.PnpmBinDir
        MySqlBinDir   = $resolved.MySqlBinDir
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

    # Run the resolver first. It reloads PATH from registry + scans registries +
    # services + common directories, then injects anything it finds into the
    # current-session $env:Path.
    $resolved = Resolve-PrerequisitePaths

    # After resolution, re-check version requirements with Python on PATH.
    $pythonOk = Test-PythonVersionOk -Config $config
    # If the version check failed but we have a PythonBinDir (version mismatch /
    # python.exe filename mismatch), keep the resolved path in $ResolvedPaths but
    # mark PythonOk as false (version still matters).

    return [PSCustomObject]@{
        Config          = $config
        IsAdmin         = Test-IsAdmin
        WingetAvailable = Test-WingetAvailable
        PythonOk        = $pythonOk
        NodeOk          = [bool](Test-CommandExists 'node') -or -not [string]::IsNullOrWhiteSpace($resolved.NodeBinDir)
        PnpmOk          = [bool](Test-CommandExists 'pnpm') -or -not [string]::IsNullOrWhiteSpace($resolved.PnpmBinDir)
        MySqlClientOk   = [bool](Test-CommandExists 'mysql') -or -not [string]::IsNullOrWhiteSpace($resolved.MySqlBinDir)
        MySqlPortOk     = Test-TcpPort -Port 3306
        MySqlService    = Test-MySqlServiceRunning -Config $config
        RedisBundledOk  = Test-Path (Join-Path (Split-Path $script:DeployScriptRoot -Parent) 'Redis\redis-server.exe')
        ResolvedPaths   = $resolved
    }
}
