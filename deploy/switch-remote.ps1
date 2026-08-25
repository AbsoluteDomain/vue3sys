# Switch git remote between GitHub and Gitea
# Usage:
#   .\switch-remote.ps1 -GiteaUrl http://gitea.your-server.com/your-name/vue3sys.git
#   .\switch-remote.ps1 -Action gitea -GiteaUrl http://10.0.0.1:3000/user/vue3sys.git
#   .\switch-remote.ps1 -Action github
#   .\switch-remote.ps1 -Action list

param(
    [ValidateSet('gitea', 'github', 'list', 'add', 'remove')]
    [string]$Action = 'list',
    [string]$GiteaUrl = '',
    [string]$RemoteName = 'origin',
    [string]$GithubUrl = 'https://github.com/AbsoluteDomain/vue3sys.git'
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_common.ps1"

$paths = Get-ProjectPaths

function Get-RemoteUrl {
    param([string]$Name)
    Push-Location $paths.ProjectRoot
    try {
        return (git remote get-url $Name 2>$null).Trim()
    } finally {
        Pop-Location
    }
}

function Set-RemoteUrl {
    param([string]$Name, [string]$Url)
    Push-Location $paths.ProjectRoot
    try {
        $existing = git remote get-url $Name 2>$null
        if ($existing) {
            Write-Step "Update remote '$Name' -> $Url"
            git remote set-url $Name $Url
        } else {
            Write-Step "Add remote '$Name' -> $Url"
            git remote add $Name $Url
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to set remote $Name"
        }
    } finally {
        Pop-Location
    }
}

function Show-Remotes {
    Push-Location $paths.ProjectRoot
    try {
        Write-Step "Current git remotes"
        $remotes = git remote -v 2>$null
        if (-not $remotes) {
            Write-Warn "No remotes configured"
            return
        }
        Write-Host $remotes
    } finally {
        Pop-Location
    }
}

# Main
Write-Step "Git remote switch (GitHub <-> Gitea)"

if ($Action -eq 'list') {
    Show-Remotes
    $current = Get-RemoteUrl -Name $RemoteName
    if ($current) {
        if ($current -match 'gitea') {
            Write-Ok "Current origin: Gitea"
        } elseif ($current -match 'github') {
            Write-Ok "Current origin: GitHub"
        } else {
            Write-Host "Current origin: $current"
        }
    }
    exit 0
}

if ($Action -eq 'gitea') {
    if (-not $GiteaUrl) {
        $GiteaUrl = Read-Host "Enter Gitea repository URL (e.g. http://192.168.1.100:3000/user/vue3sys.git)"
    }
    if (-not $GiteaUrl) {
        throw "Gitea URL is required"
    }
    Set-RemoteUrl -Name $RemoteName -Url $GiteaUrl
    Write-Ok "Switched to Gitea: $GiteaUrl"
    Write-Host ""
    Write-Host "Test connection:" -ForegroundColor Yellow
    Write-Host "  git fetch $RemoteName" -ForegroundColor Gray
    Write-Host ""
    Write-Host "If credential prompt appears, use Gitea username and password/token" -ForegroundColor Yellow
    exit 0
}

if ($Action -eq 'github') {
    Set-RemoteUrl -Name $RemoteName -Url $GithubUrl
    Write-Ok "Switched to GitHub: $GithubUrl"
    exit 0
}

if ($Action -eq 'add') {
    $url = if ($GiteaUrl) { $GiteaUrl } else { Read-Host "Enter remote URL" }
    $name = Read-Host "Remote name [gitea]"
    if (-not $name) { $name = 'gitea' }
    if (-not $url) { throw "URL required" }
    Push-Location $paths.ProjectRoot
    try {
        git remote add $name $url
        Write-Ok "Added remote '$name': $url"
    } finally {
        Pop-Location
    }
    exit 0
}

if ($Action -eq 'remove') {
    $name = if ($RemoteName -ne 'origin') { $RemoteName } else { Read-Host "Remote name to remove" }
    Push-Location $paths.ProjectRoot
    try {
        git remote remove $name
        Write-Ok "Removed remote '$name'"
    } finally {
        Pop-Location
    }
    exit 0
}
