@echo off
REM ============================================================================
REM Bikozava Wedding Invitation Platform — One-Click Windows Launcher (CMD)
REM ============================================================================
title Bikozava Wedding Platform
cd /d "%~dp0"

echo ============================================================================
echo   BIKOZAVA WEDDING INVITATION PLATFORM (Windows Launcher)
echo ============================================================================

REM 1. Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

REM 2. Create virtual environment if it does not exist
if not exist ".venv\Scripts\activate.bat" (
    echo [1/4] Creating Python virtual environment (.venv)...
    python -m venv .venv
)

REM 3. Activate virtual environment
call .venv\Scripts\activate.bat

REM 4. Install dependencies
echo [2/4] Checking and installing required packages...
python -m pip install --upgrade pip >nul 2>nul
pip install -r requirements.txt

REM 5. Create .env from .env.example if .env does not exist
if not exist ".env" (
    echo [3/4] Creating .env configuration file from .env.example...
    copy /Y ".env.example" ".env" >nul
    python -c "import secrets, pathlib; p = pathlib.Path('.env'); txt = p.read_text(encoding='utf-8'); p.write_text(txt.replace('replace_with_a_64_char_hex_secret_generated_via_secrets_token_hex', secrets.token_hex(32)), encoding='utf-8')"
)

echo [4/4] Starting Bikozava Server...
echo.
echo   * Public Demo Invitation (Badini): http://localhost:8000/ismail_shrin
echo   * Public Demo Invitation (Arabic): http://localhost:8000/ismail_shrin?lang=ar
echo   * Public Demo Invitation (English): http://localhost:8000/ismail_shrin?lang=en
echo   * Admin Studio Login:              http://localhost:8000/admin/login
echo     (Default Admin: admin / ChangeThisStrongPassword!2026)
echo.
python run.py
pause
