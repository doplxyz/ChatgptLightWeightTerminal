@echo off
setlocal

:: ChatGPT LightWeight Terminal (CLWT) - Windows Setup Script
:: This script sets up the Python environment and installs dependencies.

:: Get the directory where this script is located
set "WORKDIR=%~dp0"
cd /d "%WORKDIR%"

echo ========================================================
echo  ChatGPT LightWeight Terminal (CLWT) Setup
echo ========================================================

:: --------------------------------------------------------
:: Check for Python installation
:: --------------------------------------------------------
set "PYTHON_CMD="

:: Check for 'python'
python --version >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"

:: If not found, check for 'py' (Python Launcher)
if not defined PYTHON_CMD (
    py --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py"
)

:: If not found, check for 'python3'
if not defined PYTHON_CMD (
    python3 --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python3"
)

if not defined PYTHON_CMD (
    echo.
    echo [ERROR] Python not found.
    echo Please install Python 3.8 or later and add it to your PATH.
    echo See "README_SETUP_WIN.md" for details.
    echo.
    pause
    exit /b 1
)

echo [INFO] Using Python: %PYTHON_CMD%
"%PYTHON_CMD%" --version

:: --------------------------------------------------------
:: Create necessary directories
:: --------------------------------------------------------
echo [INFO] Creating directories...
if not exist "applog\session" mkdir "applog\session"
if not exist "tmp1" mkdir "tmp1"
if not exist "log1" mkdir "log1"

:: --------------------------------------------------------
:: Create Virtual Environment
:: --------------------------------------------------------
if not exist "venv" (
    echo [INFO] Creating virtual environment (venv)...
    "%PYTHON_CMD%" -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Virtual environment (venv) already exists.
)

:: --------------------------------------------------------
:: Activate Virtual Environment and Install Dependencies
:: --------------------------------------------------------
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
)

echo [INFO] Installing dependencies (PyQt6, playwright)...
python -m pip install PyQt6 playwright
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [INFO] Installing Playwright browsers...
python -m playwright install chromium
if errorlevel 1 (
    echo [ERROR] Failed to install Playwright browsers.
    pause
    exit /b 1
)

:: --------------------------------------------------------
:: Setup Complete
:: --------------------------------------------------------
echo.
echo ========================================================
echo  Setup Complete!
echo  To run the application, execute:
echo    venv\Scripts\activate
echo    python ChatgptLightWeightTerminal.py
echo.
echo  Or use the run script if available.
echo ========================================================
echo.

pause
