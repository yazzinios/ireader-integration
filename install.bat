@echo off
setlocal
title Arcade Kiosk - Installer

echo ===================================================
echo     Arcade Kiosk - One-Click Installer
echo ===================================================
echo.

:: 1. Check for Python
echo [1/3] Checking for Python...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python not found. Attempting to install via winget...
    winget --version >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Winget not found. Please install Python manually from python.org.
        pause
        exit /b 1
    )
    echo [i] Installing Python 3.11 via winget...
    winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Winget installation failed. Please install Python manually.
        pause
        exit /b 1
    )
    echo [OK] Python installed! Please RESTART this script to continue.
    pause
    exit /b 0
) else (
    echo [OK] Python is already installed.
    python --version
)

:: 2. Upgrade pip
echo.
echo [2/3] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: 3. Install requirements
echo.
echo [3/3] Installing application dependencies...
if exist requirements.txt (
    python -m pip install -r requirements.txt --quiet
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Dependencies installed successfully.
    ) else (
        echo [!] Dependency installation failed.
        pause
        exit /b 1
    )
) else (
    echo [!] requirements.txt not found. Installing defaults...
    python -m pip install customtkinter pyserial pygame pillow opencv-python pynput --quiet
)

echo.
echo ===================================================
echo  SUCCESS: Your Arcade Kiosk is ready!
echo  Run the app by launching: run.bat
echo ===================================================
echo.
pause
