@echo off
title Arcade Kiosk
cd /d "%~dp0"
echo Starting Kiosk...
python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Kiosk exited with error code %ERRORLEVEL%.
    echo Check that Python is installed and requirements are met.
    pause
)
