# Recreate Python venv on this machine (required after copy from another PC)
# Use -UseUv to use uv (faster, compatible with standard venv)

param(
    [switch]$SkipFrontend,
    [switch]$UseUv
)

$ErrorActionPreference = 'Stop'
$params = @{ RecreateVenv = $true }
if ($SkipFrontend) { $params.SkipFrontend = $true }
if ($UseUv) { $params.UseUv = $true }

& "$PSScriptRoot\install-deps.ps1" @params
