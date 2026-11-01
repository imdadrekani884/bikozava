@echo off
title Bikozava - Push Project to GitHub (Windows)
echo ============================================================================
echo   BIKOZAVA — ONE-CLICK GITHUB UPLOAD HELPER (WINDOWS)
echo ============================================================================
echo.

where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git is not installed on your Windows PC.
    echo Please download and install Git from: https://git-scm.com/download/win
    pause
    exit /b 1
)

if not exist ".git" (
    echo [1/4] Initializing Git repository...
    git init
    git branch -M main
)

echo [2/4] Staging all project files (excluding .env secrets via .gitignore)...
git add .
git commit -m "Deploy Bikozava luxury wedding invitation platform (24 templates + Dark Mode + Security)"

echo.
set /p REPO_URL="Paste your GitHub Repository URL (e.g. https://github.com/YOUR_USERNAME/bikozava.git): "
if "%REPO_URL%"=="" (
    echo [INFO] No repository URL entered. Commit is ready locally.
    pause
    exit /b 0
)

git remote remove origin >nul 2>nul
git remote add origin %REPO_URL%

echo [3/4] Pushing code to GitHub (main branch)...
git push -u origin main

echo.
echo [4/4] Done! Now open https://dashboard.render.com and connect this GitHub repo.
pause
