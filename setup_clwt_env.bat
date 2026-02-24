@echo off
setlocal

rem ChatGPT LightWeight Terminal (CLWT) - Windows Setup Script

set "WORKDIR=%~dp0"
cd /d "%WORKDIR%"

echo System: Starting CLWT initial setup for Windows.

rem Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not found in PATH.
    echo Please install Python and add it to your PATH.
    pause
    exit /b 1
)

rem 1. Create subfolders
if not exist "applog\session" mkdir "applog\session"
if not exist "tmp1" mkdir "tmp1"
if not exist "log1" mkdir "log1"

rem 2. Create Python virtual environment (venv)
if not exist "venv" (
    echo System: Creating Python virtual environment [venv]...
    python -m venv venv
) else (
    echo System: venv already exists.
)

rem 3. Activate virtual environment
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)

rem 4. Install libraries
echo System: Installing PyQt6 and Playwright...
python -m pip install --upgrade pip
python -m pip install PyQt6 playwright

rem 5. Install Playwright browser
echo System: Installing Chromium for Playwright...
playwright install chromium

echo ========================================================
echo System: Setup complete.
echo System: Run "python ChatgptLightWeightTerminal.py" to start.
echo ========================================================

pause
