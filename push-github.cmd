@echo off
setlocal
cd /d "%~dp0"

set GH=%TEMP%\gh_cli\bin\gh.exe
if not exist "%GH%" set GH=gh

echo Checking GitHub login...
"%GH%" auth status >nul 2>&1
if errorlevel 1 (
    echo.
    echo Not logged in. Run this first, then run push-github.cmd again:
    echo   "%GH%" auth login
    echo.
    pause
    exit /b 1
)

echo Creating public repo interview-coach and pushing...
"%GH%" repo create interview-coach --public --source=. --remote=origin --push

if errorlevel 1 (
    echo.
    echo If repo already exists, try:
    echo   git remote add origin https://github.com/YOUR_USERNAME/interview-coach.git
    echo   git push -u origin main
    pause
    exit /b 1
)

echo.
echo Done! Open your repo:
"%GH%" repo view --web
pause
