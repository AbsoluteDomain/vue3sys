@echo off
chcp 65001 >nul
title 打包 vue3sys 部署压缩包

set "ROOT=%~dp0.."
set "OUT=%~dp0..\vue3sys-deploy.zip"

echo 源目录: %ROOT%
echo 输出:   %OUT%
echo 排除: node_modules, venv, .git, __pycache__, dist, .vite
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = (Resolve-Path '%ROOT%').Path; ^
   $out = Join-Path (Split-Path $root -Parent) 'vue3sys-deploy.zip'; ^
   $stage = Join-Path $env:TEMP ('vue3sys-pack-' + [guid]::NewGuid().ToString('N')); ^
   New-Item -ItemType Directory -Path $stage | Out-Null; ^
   $exclude = @('node_modules','venv','.git','__pycache__','.pytest_cache','dist','.vite','htmlcov'); ^
   robocopy $root $stage /E /XD $exclude /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null; ^
   if (Test-Path $out) { Remove-Item $out -Force }; ^
   Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $out -CompressionLevel Optimal; ^
   Remove-Item $stage -Recurse -Force; ^
   Write-Host ('完成: ' + $out) -ForegroundColor Green"

echo.
pause
