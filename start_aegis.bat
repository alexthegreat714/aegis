@echo off
REM Aegis Control Console v0.1
REM Windows launcher and supervisor for Aegis agent

setlocal enabledelayedexpansion

:MENU
cls
echo ========================================
echo   AEGIS CONTROL CONSOLE (v0.1)
echo ========================================
echo.
echo   1) Run Aegis in interactive mode
echo   2) Run Aegis in autonomous mode
echo   3) Test OWUI connection
echo   4) View latest log file
echo   5) Open sandbox revisions folder
echo   6) Approve pending revision
echo   7) Kill all Aegis processes
echo   8) Exit
echo.
echo ========================================
set /p choice="Select option (1-8): "

if "%choice%"=="1" goto INTERACTIVE
if "%choice%"=="2" goto AUTONOMOUS
if "%choice%"=="3" goto TEST_CONNECTION
if "%choice%"=="4" goto VIEW_LOG
if "%choice%"=="5" goto OPEN_SANDBOX
if "%choice%"=="6" goto APPROVE_REVISION
if "%choice%"=="7" goto KILL_PROCESSES
if "%choice%"=="8" goto EXIT
echo Invalid choice. Press any key to retry...
pause >nul
goto MENU

:INTERACTIVE
echo.
echo [Aegis Console] Starting in INTERACTIVE mode...
echo [Aegis Console] Verbose reasoning enabled, 60s pause windows active
echo.
python aegis.py --interactive
if errorlevel 1 (
    echo.
    echo [ERROR] Aegis exited with error code %errorlevel%
    echo [ERROR] Check logs for details
)
echo.
pause
goto MENU

:AUTONOMOUS
echo.
echo [Aegis Console] Starting in AUTONOMOUS mode...
echo [Aegis Console] Auto-continue enabled (still pauses for high-risk actions)
echo.
set /p task="Enter task prompt: "
if "%task%"=="" (
    echo [ERROR] No task provided
    pause
    goto MENU
)
python aegis.py --run --prompt "%task%"
if errorlevel 1 (
    echo.
    echo [ERROR] Aegis exited with error code %errorlevel%
    echo [ERROR] Check logs for details
)
echo.
pause
goto MENU

:TEST_CONNECTION
echo.
echo [Aegis Console] Testing OpenWebUI connection...
echo.
python aegis.py --test-connection
if errorlevel 1 (
    echo.
    echo [ERROR] Connection test failed
    echo [ERROR] Check:
    echo   - OpenWebUI running on http://127.0.0.1:3000
    echo   - Token in config\.owui_token is valid
    echo   - Model 'aegis' exists in OWUI
) else (
    echo.
    echo [SUCCESS] Connection test passed
)
echo.
pause
goto MENU

:VIEW_LOG
echo.
echo [Aegis Console] Finding latest log file...
echo.

REM Find the most recent JSONL log file
set "latest_log="
for /f "delims=" %%f in ('dir /b /od /a-d data\logs\*.jsonl 2^>nul') do set "latest_log=%%f"

if "%latest_log%"=="" (
    echo [ERROR] No log files found in data\logs\
    pause
    goto MENU
)

echo [Aegis Console] Opening: data\logs\%latest_log%
echo.
notepad "data\logs\%latest_log%"
goto MENU

:OPEN_SANDBOX
echo.
echo [Aegis Console] Opening sandbox revisions folder...
echo.

REM Create revisions folder if it doesn't exist
if not exist "sandbox\revisions" (
    mkdir "sandbox\revisions"
    echo [Aegis Console] Created sandbox\revisions\ directory
)

explorer "sandbox\revisions"
goto MENU

:APPROVE_REVISION
echo.
echo [Aegis Console] Pending revisions:
echo.

REM List pending revisions
set "found_pending="
for /f "delims=" %%d in ('dir /b /ad sandbox\revisions 2^>nul') do (
    if exist "sandbox\revisions\%%d\PENDING_APPROVAL" (
        echo   - %%d
        set "found_pending=1"
    )
)

if not defined found_pending (
    echo   [None - all revisions applied or rejected]
    echo.
    pause
    goto MENU
)

echo.
set /p rev_name="Enter revision name to approve (or 'cancel'): "

if "%rev_name%"=="cancel" goto MENU
if "%rev_name%"=="" (
    echo [ERROR] No revision name provided
    pause
    goto MENU
)

echo.
echo [Aegis Console] Approving revision: %rev_name%
python aegis.py --approve-revision "%rev_name%"

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to approve revision
    echo [ERROR] Check logs or revision contents
) else (
    echo.
    echo [SUCCESS] Revision approved and applied
)
echo.
pause
goto MENU

:KILL_PROCESSES
echo.
echo [Aegis Console] Searching for Aegis processes...
echo.

REM Find Python processes running aegis.py
for /f "tokens=2" %%i in ('tasklist /v /fi "IMAGENAME eq python.exe" ^| findstr /i "aegis"') do (
    echo [Aegis Console] Killing PID %%i
    taskkill /F /PID %%i >nul 2>&1
)

echo [Aegis Console] All Aegis processes terminated
echo.
pause
goto MENU

:EXIT
echo.
echo [Aegis Console] Exiting...
exit /b 0
