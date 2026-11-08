# ============================================================================
# Bikozava — Secure One-Click GitHub Upload Script (Windows PowerShell)
# Default Repository: https://github.com/imdadrekani884/bikozava.git
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Yellow
Write-Host "  BIKOZAVA — SECURE GITHUB UPLOAD HELPER (WINDOWS POWERSHELL)" -ForegroundColor Yellow
Write-Host "  Default Repository: https://github.com/imdadrekani884/bikozava.git" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Yellow
Write-Host ""

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Git is not installed on your Windows PC." -ForegroundColor Red
    Write-Host "Download and install Git for Windows from: https://git-scm.com/download/win" -ForegroundColor Cyan
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/5] Running Pre-Commit Security & Secret Scanner..." -ForegroundColor Cyan
if (Test-Path ".venv\Scripts\python.exe") {
    & .\.venv\Scripts\python.exe scripts\scan_secrets.py
} else {
    & python scripts\scan_secrets.py
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ABORTED] Secret scanner detected potential secrets. Fix before pushing!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path ".git")) {
    Write-Host "[2/5] Initializing Git repository..." -ForegroundColor Cyan
    git init
    git branch -M main
}

# Ensure .env is never tracked
git rm --cached -f .env 2>$null
git rm --cached -r -f instance/ 2>$null

Write-Host "[3/5] Staging project files (.env and database are safely excluded by .gitignore)..." -ForegroundColor Cyan
git add .
git commit -m "Security-hardened production release of Bikozava Wedding Platform (26 templates + Supabase RLS)"

$defaultRepo = "https://github.com/imdadrekani884/bikozava.git"
$repoUrl = Read-Host "Press ENTER for [$defaultRepo] or paste custom GitHub URL"
if ([string]::IsNullOrWhiteSpace($repoUrl)) {
    $repoUrl = $defaultRepo
}

git remote remove origin 2>$null
git remote add origin $repoUrl

Write-Host "[4/5] Pushing code to $repoUrl (main branch)..." -ForegroundColor Cyan
git push -u origin main

Write-Host ""
Write-Host "[5/5] Success! Next step: Connect $repoUrl on https://dashboard.render.com" -ForegroundColor Green
Read-Host "Press Enter to finish"
