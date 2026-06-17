# 仅检查系统前置环境（不安装）

& "$PSScriptRoot\install-prerequisites.ps1" -CheckOnly
exit $LASTEXITCODE
