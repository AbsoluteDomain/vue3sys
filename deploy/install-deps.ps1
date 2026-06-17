# Install venv, pip, pnpm (ASCII-only)

param(
    [switch]$SkipFrontend,
    [switch]$RecreateVenv
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths

if (-not (Test-CommandExists 'python')) {
    throw "python not found. Install Python 3.10-3.14 and add to PATH"
}

$venvDir = Join-Path $paths.BackendRoot 'venv'

function Test-VenvUsable {
    if (-not (Test-Path $paths.VenvPython)) { return $false }
    try {
        $ver = & $paths.VenvPython --version 2>&1
        return ($LASTEXITCODE -eq 0) -and ($ver -match 'Python')
    } catch {
        return $false
    }
}

if ($RecreateVenv -and (Test-Path $venvDir)) {
    Write-Step "Recreate venv: remove old folder"
    Remove-Item -Path $venvDir -Recurse -Force
}

Write-Step "Create Python venv"
if (-not (Test-VenvUsable)) {
    if (Test-Path $venvDir) {
        Write-Warn "Broken venv detected (copied from another PC?). Removing..."
        Remove-Item -Path $venvDir -Recurse -Force
    }
    & python -m venv $venvDir
    if (-not (Test-VenvUsable)) {
        throw "Failed to create venv at $venvDir"
    }
    Write-Ok "venv created: $venvDir"
} else {
    Write-Ok "venv OK"
}

Write-Step "Install Python packages"
Push-Location $paths.BackendRoot
& $paths.VenvPip install --upgrade pip
& $paths.VenvPip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "pip install failed"
}
Pop-Location
Write-Ok "Python deps OK"

Write-Step "Django check and migrate"
Push-Location $paths.BackendRoot
& $paths.VenvPython manage.py check
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "django check failed. Check .env and MySQL service"
}
& $paths.VenvPython manage.py migrate --noinput 2>&1 | Out-Host
Pop-Location
Write-Ok "migrate OK"

if (-not $SkipFrontend) {
    Write-Step "Install frontend deps"
    $nodeModules = Join-Path $paths.FrontendRoot 'node_modules'
    if (Test-Path $nodeModules) {
        Write-Warn "node_modules exists. If copied from another PC, delete it and re-run."
    }
    if (-not (Test-CommandExists 'pnpm')) {
        Write-Warn "pnpm not found, trying npm install -g pnpm"
        if (Test-CommandExists 'npm') {
            & npm install -g pnpm
        } else {
            throw "Install Node.js and pnpm first"
        }
    }
    Push-Location $paths.FrontendRoot
    & pnpm install
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "pnpm install failed"
    }
    Pop-Location
    Write-Ok "Frontend deps OK"
}

Write-Ok "Done. Next: import-database.ps1 or start-all.ps1"
