@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d C:\Users\blyth\aegis

REM Force UTF-8 for any output
set PYTHONUTF8=1

REM Prefer py if available, else python
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 bootstrap_repo.py
) else (
  python bootstrap_repo.py
)

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo [ERROR] Bootstrap failed. Check the messages above.
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo [OK] Aegis repo pushed. You can switch to Claude Code now.
pause
