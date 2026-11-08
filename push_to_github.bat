@echo off
title Bikozava - Push Hardened Project to GitHub (Windows)
echo ============================================================================
echo   BIKOZAVA — SECURE GITHUB UPLOAD HELPER (WINDOWS)
echo   Default Repository: https://github.com/imdadrekani884/bikozava.git
echo ============================================================================
echo.

where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git is not installed on your Windows PC.
    echo Please download and install Git from: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo [1/5] Running Pre-Commit Security ^& Secret Scanner...
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe scripts\scan_secrets.py
) else (
    python scripts\scan_secrets.py
)
if %ERRORLEVEL% neq 0 (
    echo [ABORTED] Secret scanner detected potential secrets. Fix before pushing!
    pause
    exit /b 1
)

if not exist ".git" (
    echo [2/5] Initializing Git repository...
    git init
    git branch -M main
)

REM Ensure .env and local SQLite databases are never staged even if previously tracked
git rm --cached -f .env >nul 2>nul
git rm --cached -r -f instance/ >nul 2>nul

echo [3/5] Staging project files (excluding .env secrets via .gitignore)...
git add .
git commit -m "Security-hardened production release of Bikozava Wedding Platform (26 templates + Supabase RLS)"

echo.
set DEFAULT_REPO=https://github.com/imdadrekani884/bikozava.git
set /p REPO_URL="Press ENTER for [%DEFAULT_REPO%] or paste custom URL: "
if "%REPO_URL%"=="" set REPO_URL=%DEFAULT_REPO%

git remote remove origin >nul 2>nul
git remote add origin %REPO_URL%

echo [4/5] Pushing code to %REPO_URL% (main branch)...
git push -u origin main

echo.
echo [5/5] Done! Your repository is updated at: %REPO_URL%
pause
