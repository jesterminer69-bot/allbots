@echo off
setlocal
title Profit GitHub Update - Once
cd /d "%~dp0"
echo ============================================================
echo Profit GitHub Status Update - One Run
echo ============================================================
echo.
py -3 github_update.py --once --config config.json
if errorlevel 1 (
  echo.
  echo Update failed. Read the message above.
  pause
  exit /b 1
)
echo.
echo Done.
pause
