@echo off
setlocal
title Profit GitHub Update - Every 5 Minutes
cd /d "%~dp0"
echo ============================================================
echo Profit GitHub Status Update Loop
echo ============================================================
echo.
echo This updates data\status.json and pushes to GitHub every 5 minutes.
echo Press Ctrl+C to stop.
echo.
py -3 github_update.py --loop --config config.json
pause
