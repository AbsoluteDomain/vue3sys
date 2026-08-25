# Build frontend for production (pnpm build) and copy to a standard location for Nginx.
# Run on dev machine OR target server (needs Node + pnpm).

param(
    [switch]$SkipNginxConfig
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths

Write-Step "Prepare frontend .env.production"
$feProdEnvPath = Join-Path $paths.FrontendRoot '.env.production'
$feProdTplPath = Join-Path $paths.DeployRoot 'templates\frontend.env.production.template'
if (-not (Test-Path $feProdEnvPath) -and (Test-Path $feProdTplPath)) {
    Copy-Item $feProdTplPath $feProdEnvPath -Force
    Write-Ok "Created .env.production from template"
}

if (-not (Test-CommandExists 'pnpm')) {
    if (Test-CommandExists 'npm') {
        Write-Step "Install pnpm global"
        & npm install -g pnpm
        Refresh-SessionPath
    } else {
        throw "pnpm not found and npm not found. Install Node.js first."
    }
}

Write-Step "Install frontend deps (pnpm install)"
Push-Location $paths.FrontendRoot
& pnpm install
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "pnpm install failed" }
Pop-Location
Write-Ok "Frontend deps OK"

Write-Step "pnpm build (production)"
Push-Location $paths.FrontendRoot
& pnpm build
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "pnpm build failed" }
Pop-Location

$dist = Join-Path $paths.FrontendRoot 'dist'
if (-not (Test-Path (Join-Path $dist 'index.html'))) {
    throw "Build succeeded but dist/index.html not found in $dist"
}
$size = (Get-ChildItem $dist -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Ok "Build OK: $dist ($([math]::Round($size, 1)) MB)"

# Copy nginx.conf.template next to dist so customer can just point nginx root to dist
if (-not $SkipNginxConfig) {
    $nginxTpl = Join-Path $paths.DeployRoot 'templates\nginx.conf.template'
    if (Test-Path $nginxTpl) {
        $nginxConf = Join-Path $dist 'nginx.example.conf'
        $content = Get-Content $nginxTpl -Raw -Encoding UTF8
        $content = $content -replace '\{\{PROJECT_ROOT\}\}', ($paths.ProjectRoot -replace '\\', '/')
        [System.IO.File]::WriteAllText($nginxConf, $content, [System.Text.UTF8Encoding]::new($false))
        Write-Ok "Example nginx config: $nginxConf"
    }
}

Write-Host ""
Write-Ok "Frontend build complete"
Write-Host "  Dist dir : $dist" -ForegroundColor Gray
Write-Host "  Copy dist to server and point Nginx to it." -ForegroundColor Yellow
Write-Host "  For backend: run youlai-django\venv\Scripts\daphne.exe -b 0.0.0.0 -p 8000 config.asgi:application" -ForegroundColor Yellow
Write-Host "  For static/admin: youlai-django\venv\Scripts\python.exe manage.py collectstatic --noinput" -ForegroundColor Gray
