# Temporary diagnostic to validate resolver
$ErrorActionPreference = 'Continue'
. 'C:\work\vue3sys\deploy\_common.ps1'
Write-Host "== Resolve-PrerequisitePaths ==" -ForegroundColor Cyan
$r = Resolve-PrerequisitePaths
$r | Format-List *
Write-Host ""
Write-Host "== Post-resolve command checks ==" -ForegroundColor Cyan
foreach ($c in @('python','node','mysql','pnpm','py','npm')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) {
        Write-Host ("[OK] {0,-7} -> {1}" -f $c, $cmd.Source) -ForegroundColor Green
    } else {
        Write-Host ("[XX] {0,-7} not found in current session PATH" -f $c) -ForegroundColor Yellow
    }
}
Write-Host ""
Write-Host "== Get-PrerequisiteStatus summary ==" -ForegroundColor Cyan
$s = Get-PrerequisiteStatus
Write-Host ("PythonOk=`t{0}`nNodeOk=`t{1}`nPnpmOk=`t{2}`nMySqlClientOk=`t{3}`nMySqlPortOk=`t{4}`nMySqlService=`t{5} {6}" -f $s.PythonOk,$s.NodeOk,$s.PnpmOk,$s.MySqlClientOk,$s.MySqlPortOk,$s.MySqlService.ServiceName,$s.MySqlService.Status)
Write-Host "`nResolved:"
$s.ResolvedPaths | Format-List *
