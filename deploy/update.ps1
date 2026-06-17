# Pull latest code on an already-deployed server, sync deps, migrate, then restart.
# Does NOT overwrite .env / redis.windows.conf (not in git).

param(
    [switch]$SkipFrontend,
    [switch]$SkipMigrate,
    [switch]$SkipDeps,
    [switch]$NoStart,
    [string]$Branch = ''
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths

function Test-GitRepo {
    Push-Location $paths.ProjectRoot
    try {
        $null = git rev-parse --is-inside-work-tree 2>$null
        return ($LASTEXITCODE -eq 0)
    } finally {
        Pop-Location
    }
}

function Get-GitBranch {
    Push-Location $paths.ProjectRoot
    try {
        $current = (git branch --show-current 2>$null).Trim()
        if ($current) { return $current }
        return 'master'
    } finally {
        Pop-Location
    }
}

function Assert-LocalConfig {
    if (-not (Test-Path $paths.BackendEnv)) {
        throw "Missing $($paths.BackendEnv). This script is for servers already configured with configure.ps1"
    }
    if (-not (Test-Path $paths.VenvPython)) {
        throw "Missing venv. Run install-deps.ps1 or recreate-venv.ps1 first"
    }
}

Write-Step "vue3sys code update (keeps local .env and database)"

if (-not (Test-GitRepo)) {
    throw "Not a git repo: $($paths.ProjectRoot)"
}

Assert-LocalConfig

Push-Location $paths.ProjectRoot
try {
    $targetBranch = if ($Branch) { $Branch } else { Get-GitBranch }

    Write-Step "Check working tree"
    $statusLines = git status --porcelain 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git status failed"
    }
    if ($statusLines) {
        Write-Warn "Local changes detected. git pull may fail or merge."
        Write-Host ($statusLines | Out-String)
        $continue = Read-Host "Continue pull anyway? (y/N)"
        if ($continue -ne 'y' -and $continue -ne 'Y') {
            throw "Update cancelled"
        }
    } else {
        Write-Ok "Working tree clean"
    }

    Write-Step "git pull origin $targetBranch"
    git pull origin $targetBranch
    if ($LASTEXITCODE -ne 0) {
        throw "git pull failed"
    }
    Write-Ok "Code updated"
} finally {
    Pop-Location
}

if (-not $SkipDeps) {
    Write-Step "Sync Python dependencies"
    Push-Location $paths.BackendRoot
    & $paths.VenvPip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "pip install failed"
    }
    Pop-Location
    Write-Ok "Python deps OK"

    if (-not $SkipFrontend) {
        if (Test-CommandExists 'pnpm') {
            Write-Step "Sync frontend dependencies"
            Push-Location $paths.FrontendRoot
            & pnpm install
            if ($LASTEXITCODE -ne 0) {
                Pop-Location
                throw "pnpm install failed"
            }
            Pop-Location
            Write-Ok "Frontend deps OK"
        } else {
            Write-Warn "pnpm not found, skip frontend deps"
        }
    }
}

if (-not $SkipMigrate) {
    Write-Step "Database migrate"
    Push-Location $paths.BackendRoot
    & $paths.VenvPython manage.py migrate --noinput 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "migrate failed"
    }
    Pop-Location
    Write-Ok "migrate OK"
}

Write-Step "Django check"
Push-Location $paths.BackendRoot
& $paths.VenvPython manage.py check 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "django check failed"
}
Pop-Location
Write-Ok "django check OK"

Write-Host ""
Write-Host "Next: close old Vue3Sys-Redis / Vue3Sys-Django / Vue3Sys-Frontend windows, then restart." -ForegroundColor Yellow

if (-not $NoStart) {
    Write-Step "Restart services"
    & "$PSScriptRoot\start-all.ps1" @(
        if ($SkipFrontend) { '-SkipFrontend' }
    )
} else {
    Write-Ok "Update done. Restart services manually: deploy\start-all.ps1"
}
