# ============================================================================
# BIKOZAVA — ONE-CLICK GITHUB UPLOAD HELPER (`push_to_github.ps1`)
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Yellow
Write-Host "  BIKOZAVA — GITHUB UPLOAD HELPER (WINDOWS POWERSHELL)" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Yellow

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Git is not installed. Download it from https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".git")) {
    Write-Host "[1/4] Initializing Git repository..." -ForegroundColor Cyan
    git init
    git branch -M main
}

Write-Host "[2/4] Staging project files (excluding .env secrets via .gitignore)..." -ForegroundColor Cyan
git add .
git commit -m "Deploy Bikozava wedding invitation platform (24 templates + Dark Mode + Render Ready)"

$RepoUrl = Read-Host "Paste your GitHub Repository URL (e.g. https://github.com/YOUR_USERNAME/bikozava.git)"
if ($RepoUrl) {
    git remote remove origin 2>$null
    git remote add origin $RepoUrl
    Write-Host "[3/4] Pushing to GitHub..." -ForegroundColor Cyan
    git push -u origin main
    Write-Host "[4/4] Successfully pushed to GitHub! Connect your repo at https://dashboard.render.com" -ForegroundColor Green
}
