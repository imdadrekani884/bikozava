# =============================================================================
# Bikozava Wedding Invitation Platform — Windows PowerShell Launcher
# Usage: .\start_windows.ps1
# =============================================================================
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "============================================================================" -ForegroundColor Yellow
Write-Host "  BIKOZAVA WEDDING INVITATION PLATFORM (Windows PowerShell)" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Yellow

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python was not found in PATH. Install Python 3.10+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "[1/4] Creating virtual environment (.venv)..." -ForegroundColor Cyan
    python -m venv .venv
}

Write-Host "[2/4] Activating virtual environment & installing dependencies..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip | Out-Null
& ".\.venv\Scripts\pip.exe" install -r requirements.txt

if (-not (Test-Path ".env")) {
    Write-Host "[3/4] Creating .env from .env.example with a fresh cryptographic SECRET_KEY..." -ForegroundColor Cyan
    Copy-Item ".env.example" ".env"
    & ".\.venv\Scripts\python.exe" -c "import secrets, pathlib; p = pathlib.Path('.env'); txt = p.read_text(encoding='utf-8'); p.write_text(txt.replace('replace_with_a_64_char_hex_secret_generated_via_secrets_token_hex', secrets.token_hex(32)), encoding='utf-8')"
}

Write-Host "[4/4] Starting Bikozava Server on http://localhost:8000 ..." -ForegroundColor Green
Write-Host ""
Write-Host "  * Demo Invitation (Badini):  http://localhost:8000/ismail_shrin" -ForegroundColor White
Write-Host "  * Demo Invitation (Arabic):  http://localhost:8000/ismail_shrin?lang=ar" -ForegroundColor White
Write-Host "  * Demo Invitation (English): http://localhost:8000/ismail_shrin?lang=en" -ForegroundColor White
Write-Host "  * Admin Studio Login:        http://localhost:8000/admin/login" -ForegroundColor Yellow
Write-Host "    (Default Admin: admin / ChangeThisStrongPassword!2026)" -ForegroundColor Gray
Write-Host ""

& ".\.venv\Scripts\python.exe" run.py
