@echo off
setlocal

rem ChatGPT LightWeight Terminal (CLWT) - Windows Setup Script

set "WORKDIR=%~dp0"
cd /d "%WORKDIR%"

echo System: Starting CLWT initial setup for Windows.

rem 1. Create subfolders
if not exist "applog\session" mkdir "applog\session"
if not exist "tmp1" mkdir "tmp1"
if not exist "log1" mkdir "log1"

rem 2. Create Python virtual environment (venv)
if not exist "venv" (
    echo System: Creating Python virtual environment (venv)...
    python -m venv venv
) else (
    echo System: venv already exists.
)

rem 3. Activate virtual environment
call venv\Scripts\activate.bat

rem 4. Install libraries
echo System: Installing PyQt6 and Playwright...
pip install --upgrade pip
pip install PyQt6 playwright

rem 5. Install Playwright browser
echo System: Installing Chromium for Playwright...
playwright install chromium

echo ========================================================
echo System: Setup complete.
echo System: Run "python ChatgptLightWeightTerminal.py" to start.
echo ========================================================

pause
