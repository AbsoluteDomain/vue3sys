@echo off
REM =========================================================
REM   vue3sys - 打包项目成 zip（给客户机一键部署用）
REM
REM   关键设计：
REM     - 所有 PowerShell 逻辑放在 pack-project.ps1，本 bat 只做调用。
REM       避免旧写法里用 ^ 续行拼超长 powershell -Command 导致 CMD/PS 解析错误而闪退。
REM     - 每个步骤检测 errorlevel，失败就 goto :error 并 pause。
REM       保证无论哪一步失败，窗口都不会立即消失，用户一定能看到报错和日志路径。
REM     - 全程 stdout+stderr 写入 logs\pack-yyyyMMdd_HHmmss.log，失败时提示打开日志。
REM =========================================================

setlocal EnableExtensions
chcp 65001 >nul

REM --- (1) 定位 deploy 目录 ---
cd /d "%~dp0"
set "DEPLOY_DIR=%~dp0"
set "PROJECT_ROOT=%~dp0.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
for %%I in ("%DEPLOY_DIR%") do set "DEPLOY_DIR=%%~fI"

REM --- (2) 准备 logs 目录 + 日志文件 ---
if not exist "%DEPLOY_DIR%logs" mkdir "%DEPLOY_DIR%logs"
set "LOG_FILE=%DEPLOY_DIR%logs\pack-%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"
set "LOG_FILE=%LOG_FILE: =0%"

title vue3sys Pack Project

REM --- (3) 开场白 ---
cls
echo.
echo ============================================================
echo   vue3sys Pack Project
echo ============================================================
echo   Project root : %PROJECT_ROOT%
echo   Deploy dir   : %DEPLOY_DIR%
echo   Log file     : %LOG_FILE%
echo.
echo   This script will create vue3sys-deploy.zip next to the
echo   project root, for one-click customer deployment.
echo.
echo   [Tip] For offline customers, run first:
echo         powershell -ExecutionPolicy Bypass -File "%DEPLOY_DIR%pack-offline-deps.ps1"
echo ============================================================
echo.

REM --- (4) 检查关键脚本存在 ---
if not exist "%DEPLOY_DIR%pack-project.ps1" (
    echo [FATAL] pack-project.ps1 missing in: %DEPLOY_DIR%
    goto error
)
if not exist "%DEPLOY_DIR%_common.ps1" (
    echo [FATAL] _common.ps1 missing in: %DEPLOY_DIR%
    goto error
)

REM --- (5) 检查 PowerShell 是否可用 ---
where powershell >nul 2>&1
if errorlevel 1 (
    echo [FATAL] powershell.exe not found in PATH. This requires Windows PowerShell 5.1+.
    goto error
)

REM --- (6) 调用 pack-project.ps1 （带 tee 写入日志） ---
echo [Step 1/2] Running pack-project.ps1 ...
echo         Tip: no prompts. Can take 2-10 min if dist/ or offline bundles exist.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%DEPLOY_DIR%pack-project.ps1" 2>&1 | tee "%LOG_FILE%"

REM NOTE: when piping via | tee the errorlevel from powershell is not propagated
REM through %errorlevel%; detect failure via log or run again to capture exit separately.
set "PSEXIT=%ERRORLEVEL%"

REM Re-run via a direct invocation to get the real exit code, and append to log if tee lost output.
if exist "%LOG_FILE%" (
    findstr /i /c:"PACK COMPLETE" "%LOG_FILE%" >nul 2>&1
    if errorlevel 1 (
        REM 明确以退出码为准再跑一次
        echo.
        echo [Retrying with direct execution for diagnostic exit code...]
        echo. >> "%LOG_FILE%"
        echo ============= Direct PS invocation (exit code capture) ============ >> "%LOG_FILE%"
        powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%DEPLOY_DIR%pack-project.ps1" 2>&1 >> "%LOG_FILE%"
        set "PSEXIT=%ERRORLEVEL%"
    ) else (
        set "PSEXIT=0"
    )
) else (
    echo [FATAL] Log file was not generated: %LOG_FILE%
    goto error
)

REM --- (7) 根据退出码决定成功 / 失败 ---
if "%PSEXIT%"=="0" (
    echo.
    echo ============================================================
    echo   ^>^>^> PACK SUCCESS ^<^<^<
    echo ============================================================
    echo   Zip is next to the project root folder.
    echo   Full log: %LOG_FILE%
    echo ============================================================
    echo.
    goto end
)

echo.
echo [FATAL] pack-project.ps1 returned non-zero exit code: %PSEXIT%
goto error

REM =========================================================
:error
REM 任何失败跳这里，永远 pause 不闪退
REM =========================================================
echo.
echo ============================================================
echo   !! PACK FAILED !!
echo ============================================================
echo   Please read the error above carefully.
echo   If nothing useful above, open the log file:
echo     %LOG_FILE%
echo.
echo   Common fixes:
echo     1. If offline_packages missing: run pack-offline-deps.ps1 first (optional, warning only).
echo     2. Close programs that lock files (IDE, browser, services using dist/).
echo     3. Ensure write permission to: %PROJECT_ROOT% (parent dir).
echo     4. If this bat was opened as non-admin, retry by right-click -^> Run as administrator.
echo ============================================================
echo.
pause
endlocal
exit /b 1

REM =========================================================
:end
REM 成功也停一下，让用户看 zip 路径信息
REM =========================================================
pause
endlocal
exit /b 0
