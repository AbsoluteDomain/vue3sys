# Convert all .bat files in deploy dir to encoding consistent with CMD default code page.
#
# Root cause of the user's "不是内部或外部命令" flood:
#   CMD default on zh-CN Windows runs with chcp 936 (GBK/DBCS).  If a .bat file is
#   saved as UTF-8 / UTF-8 BOM / UTF-8 NO BOM and contains CJK characters, CMD's
#   parser will misinterpret CJK byte sequences as: continuation tokens, stray
#   quotes, pipe/redirect characters — which in turn causes random Chinese text
#   fragments to be executed as commands (hence: '悊鍛樿韩浠借繍琛岋墠鑳借嚜鍔ㄥ畨瑁?Python' 不是内部...).
#
# This script rewrites every .bat using GBK (codepage 936) encoding, which is what
# CMD (chcp 936) expects on Chinese Windows.  For bat files that *also* set chcp
# 65001 inside, leaving them as UTF-8 would still break parse-time, so the output
# stays GBK.
#
# After running this, you should re-run diagnose-resolver.ps1 and the 一键部署 bat.

param(
    [string]$Dir = 'C:\work\vue3sys\deploy',
    [string]$BackupDir = ''
)
$ErrorActionPreference = 'Stop'
# System.Text.Encoding is part of mscorlib / System.Private.CoreLib, no need to Add-Type.

$Dir = [System.IO.Path]::GetFullPath($Dir)
if ([string]::IsNullOrWhiteSpace($BackupDir)) {
    $BackupDir = Join-Path $Dir ("_bat_utf8_backup_{0:yyyyMMdd_HHmmss}" -f (Get-Date))
}
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$targetEnc = [System.Text.Encoding]::GetEncoding(936) # GBK / ANSI for zh-CN

$bats = Get-ChildItem -Path $Dir -File -Filter '*.bat'
$report = @()
foreach ($b in $bats) {
    # Backup original bytes
    $backupPath = Join-Path $BackupDir $b.Name
    Copy-Item $b.FullName $backupPath -Force

    $bytes = [System.IO.File]::ReadAllBytes($b.FullName)
    # Detect source encoding with simple BOM check + fallbacks
    $srcEnc = $null
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $srcEnc = [System.Text.Encoding]::UTF8
        $text = [System.Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
    } elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
        $srcEnc = [System.Text.Encoding]::Unicode
        $text = [System.Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
    } elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) {
        $srcEnc = [System.Text.Encoding]::BigEndianUnicode
        $text = [System.Text.Encoding]::BigEndianUnicode.GetString($bytes, 2, $bytes.Length - 2)
    } else {
        # No BOM. Try UTF-8 strict first; fall back to current ANSI (936 on zh-CN).
        try {
            $utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)
            $text = $utf8Strict.GetString($bytes)
            $srcEnc = [System.Text.Encoding]::UTF8
        } catch {
            $text = $targetEnc.GetString($bytes)
            $srcEnc = $targetEnc
        }
    }

    # Common safety: remove leading BOM chars that may survive as ZERO WIDTH chars
    $text = $text.TrimStart([char]0xFEFF, [char]0xFFFE, "`r","`n")

    # Rewrite in GBK (no BOM)
    $outBytes = $targetEnc.GetBytes($text)
    [System.IO.File]::WriteAllBytes($b.FullName, $outBytes)

    $report += [PSCustomObject]@{
        File      = $b.Name
        SrcEnc    = $srcEnc.EncodingName
        BytesOld  = $bytes.Length
        BytesNew  = $outBytes.Length
        Backup    = $backupPath
    }
}

$report | Format-Table -AutoSize | Out-Host
Write-Host ("`nTotal bats converted: {0}. Backup folder: {1}" -f $report.Count, $BackupDir) -ForegroundColor Green
