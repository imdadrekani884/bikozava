@echo off
setlocal EnableExtensions
title Bikozava - Secure GitHub Push

echo ============================================================================
echo   BIKOZAVA - SECURE GITHUB PUSH
echo   Default Repository: https://github.com/imdadrekani884/bikozava.git
echo ====================================================================
echo.

REM ============================================================
REM 1. Check Git
REM ============================================================
where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git is not installed.
    pause
    exit /b 1
)

echo [1/7] Checking repository...

git rev-parse --is-inside-work-tree >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] This folder is not a Git repository.
    pause
    exit /b 1
)

REM ============================================================
REM 2. Secret scanner
REM ============================================================
echo.
echo [2/7] Running secret scanner...

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe scripts\scan_secrets.py
) else (
    python scripts\scan_secrets.py
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ABORTED] Secret scanner detected a potential secret.
    echo Fix the problem before pushing.
    pause
    exit /b 1
)

echo [OK] Secret scanner passed.

REM ============================================================
REM 3. Remove sensitive files from Git index
REM ============================================================
echo.
echo [3/7] Removing sensitive files from Git tracking...

git rm --cached -f "bikozava\.env" >nul 2>nul
git rm --cached -r -f "bikozava\instance" >nul 2>nul

echo [OK] Sensitive local files protected.

REM ============================================================
REM 4. Verify .env is ignored
REM ============================================================
echo.
echo [4/7] Verifying .env protection...

git check-ignore -q "bikozava\.env"

if %ERRORLEVEL% neq 0 (
    echo [ERROR] bikozava\.env is NOT ignored by Git!
    echo.
    echo Add this to bikozava\.gitignore:
    echo .env
    echo.
    echo [ABORTED] Nothing will be pushed.
    pause
    exit /b 1
)

echo [OK] .env is ignored.

REM ============================================================
REM 5. Stage files
REM ============================================================
echo.
echo [5/7] Staging project files...

git add .

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Git staging failed.
    pause
    exit /b 1
)

REM ============================================================
REM 6. Final security check
REM ============================================================
echo.
echo [6/7] Performing final Git security check...

git ls-files | findstr /i /x "bikozava/.env" >nul

if %ERRORLEVEL%==0 (
    echo [ERROR] .env is tracked!
    echo [ABORTED] Nothing will be pushed.
    git reset
    pause
    exit /b 1
)

echo [OK] Real .env is NOT tracked.

echo.
echo Current Git status:
git status --short

REM ============================================================
REM Commit
REM ============================================================
echo.
git diff --cached --quiet

if %ERRORLEVEL%==0 (
    echo [INFO] No new changes to commit.
) else (
    echo [INFO] Creating commit...
    git commit -m "Update Bikozava secure production release"

    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Commit failed.
        pause
        exit /b 1
    )
)

REM ============================================================
REM 7. Configure remote and push
REM ============================================================
echo.
echo [7/7] GitHub repository...

set "DEFAULT_REPO=https://github.com/imdadrekani884/bikozava.git"
set "REPO_URL="

set /p REPO_URL="Press ENTER for [%DEFAULT_REPO%] or paste custom URL: "

if "%REPO_URL%"=="" set "REPO_URL=%DEFAULT_REPO%"

git remote get-url origin >nul 2>nul

if %ERRORLEVEL%==0 (
    git remote set-url origin "%REPO_URL%"
) else (
    git remote add origin "%REPO_URL%"
)

echo.
echo [INFO] Pushing to:
echo %REPO_URL%
echo.

git push -u origin main

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] GitHub push failed.
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo   SUCCESS
echo   Bikozava was pushed securely to GitHub.
echo ============================================================================
echo.
echo Repository:
echo %REPO_URL%
echo.
pause