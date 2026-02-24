@echo off
setlocal

rem ChatGPT LightWeight Terminal (CLWT) - Windows Setup Script

set "WORKDIR=%~dp0"
cd /d "%WORKDIR%"

echo System: Starting CLWT initial setup for Windows.

rem --------------------------------------------------------
rem Check for Python installation
rem --------------------------------------------------------
set "PYTHON_CMD="

rem Try 'python'
python --version >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"

rem If not found, try 'py' (Python Launcher)
if not defined PYTHON_CMD (
    py --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py"
)

rem If not found, try 'python3'
if not defined PYTHON_CMD (
    python3 --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python3"
)

if not defined PYTHON_CMD (
    echo.
    echo ========================================================
    echo Error: Pythonが見つかりません。
    echo Error: Python is not installed or not found in PATH.
    echo.
    echo Pythonをインストールし、PATHに追加してください。
    echo 詳細は同梱の "README_SETUP_WIN.md" を参照してください。
    echo ========================================================
    echo.
    pause
    exit /b 1
)

echo System: Using Python executable: %PYTHON_CMD%

rem 1. Create subfolders
if not exist "applog\session" mkdir "applog\session"
if not exist "tmp1" mkdir "tmp1"
if not exist "log1" mkdir "log1"

rem 2. Create Python virtual environment (venv)
if not exist "venv" (
    echo System: Creating Python virtual environment [venv]...
    "%PYTHON_CMD%" -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
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
if %errorlevel% neq 0 (
    echo Error: Failed to upgrade pip.
    pause
    exit /b 1
)
python -m pip install PyQt6 playwright
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies.
    pause
    exit /b 1
)

rem 5. Install Playwright browser
echo System: Installing Chromium for Playwright...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo Error: Failed to install Playwright browsers.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo System: Setup complete.
echo System: Run "python ChatgptLightWeightTerminal.py" to start.
echo ========================================================
echo.

pause
