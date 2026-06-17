# Recreate Python venv on this machine (required after copy from another PC)

param(
    [switch]$SkipFrontend
)

$ErrorActionPreference = 'Stop'
$params = @{ RecreateVenv = $true }
if ($SkipFrontend) { $params.SkipFrontend = $true }

& "$PSScriptRoot\install-deps.ps1" @params
