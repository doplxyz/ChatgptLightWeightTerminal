@echo off
chcp 65001 >nul
setlocal

:: ChatGPT LightWeight Terminal (CLWT) - Windows Setup Script

set "WORKDIR=%~dp0"
cd /d "%WORKDIR%"

echo ========================================================
echo  ChatGPT LightWeight Terminal (CLWT) セットアップ
echo ========================================================

:: --------------------------------------------------------
:: Pythonのインストール確認
:: --------------------------------------------------------
set "PYTHON_CMD="

python --version >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if defined PYTHON_CMD goto :PYTHON_FOUND

py --version >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py"
if defined PYTHON_CMD goto :PYTHON_FOUND

python3 --version >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python3"
if defined PYTHON_CMD goto :PYTHON_FOUND

echo.
echo [エラー] Pythonが見つかりません。
echo Python 3.8以降をインストールし、PATHに追加してください。
echo 詳細は "README_SETUP_WIN.md" を参照してください。
echo.
pause
exit /b 1

:PYTHON_FOUND
echo [情報] 使用するPython: %PYTHON_CMD%
"%PYTHON_CMD%" --version

:: --------------------------------------------------------
:: ディレクトリの作成
:: --------------------------------------------------------
echo [情報] 必要なディレクトリを作成しています...
if not exist "applog\session" mkdir "applog\session"
if not exist "tmp1" mkdir "tmp1"
if not exist "log1" mkdir "log1"

:: --------------------------------------------------------
:: 仮想環境の作成
:: --------------------------------------------------------
if exist "venv" goto :VENV_EXISTS

echo [情報] 仮想環境 venv を作成しています...
"%PYTHON_CMD%" -m venv venv
if not errorlevel 1 goto :VENV_CREATED

echo [エラー] 仮想環境の作成に失敗しました。
pause
exit /b 1

:VENV_EXISTS
echo [情報] 仮想環境 venv は既に存在します。

:VENV_CREATED
:: --------------------------------------------------------
:: 仮想環境の有効化と依存関係のインストール
:: --------------------------------------------------------
echo [情報] 仮想環境を有効化しています...
call venv\Scripts\activate.bat
if not errorlevel 1 goto :VENV_ACTIVATED

echo [エラー] 仮想環境の有効化に失敗しました。
pause
exit /b 1

:VENV_ACTIVATED
echo [情報] pipをアップグレードしています...
python -m pip install --upgrade pip
if not errorlevel 1 goto :PIP_UPGRADED

echo [エラー] pipのアップグレードに失敗しました。
pause
exit /b 1

:PIP_UPGRADED
echo [情報] 依存関係 PyQt6, playwright をインストールしています...
python -m pip install PyQt6 playwright
if not errorlevel 1 goto :DEPS_INSTALLED

echo [エラー] 依存関係のインストールに失敗しました。
pause
exit /b 1

:DEPS_INSTALLED
echo [情報] Playwright用ブラウザをインストールしています...
python -m playwright install chromium
if not errorlevel 1 goto :BROWSER_INSTALLED

echo [エラー] Playwright用ブラウザのインストールに失敗しました。
pause
exit /b 1

:BROWSER_INSTALLED
:: --------------------------------------------------------
:: セットアップ完了
:: --------------------------------------------------------
echo.
echo ========================================================
echo  セットアップが完了しました。
echo  アプリケーションを実行するには、以下を実行してください:
echo    venv\Scripts\activate
echo    python ChatgptLightWeightTerminal.py
echo.
echo  または、実行用スクリプト run_clwt.bat を使用してください。
echo ========================================================
echo.

pause
