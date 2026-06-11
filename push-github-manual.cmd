@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo  PUSH GITHUB - TAO REPO TREN WEB (khong can gh CLI)
echo ============================================================
echo.
echo BUOC 1: Mo GitHub, tao repo MOI:
echo   - Ten: interview-coach
echo   - KHONG tick "Add README" / .gitignore
echo.
start https://github.com/new
echo.
set /p USERNAME=Nhap GitHub username cua ban: 

if "%USERNAME%"=="" (
    echo [ERROR] Chua nhap username.
    pause
    exit /b 1
)

git remote remove origin 2>nul
git remote add origin https://github.com/%USERNAME%/interview-coach.git

echo.
echo BUOC 2: Push (cua so dang nhap GitHub co the hien ra)
echo   - Username: %USERNAME%
echo   - Password: dan TOKEN ghp_... (KHONG phai mat khau GitHub)
echo.
echo Tao token tai: https://github.com/settings/tokens/new?scopes=repo
echo.
pause

git push -u origin main
if errorlevel 1 (
    echo.
    echo Push that bai. Kiem tra:
    echo   1. Da tao repo interview-coach tren GitHub chua?
    echo   2. Dung TOKEN (ghp_...) lam password, khong phai mat khau account
    pause
    exit /b 1
)

echo.
echo THANH CONG! Repo: https://github.com/%USERNAME%/interview-coach
start https://github.com/%USERNAME%/interview-coach
pause
