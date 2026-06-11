@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set GH=%TEMP%\gh_cli\bin\gh.exe
if not exist "%GH%" set GH=gh

echo ============================================================
echo  PUSH GITHUB - DUNG TOKEN (khong can dán code device)
echo ============================================================
echo.
echo BUOC 1: Tao token tren GitHub (trinh duyet se mo)
echo   - Click "Generate new token" ^(classic^)
echo   - Tick quyen: repo
echo   - Generate token ^> COPY token ^(chi hien 1 lan^)
echo.
pause
start https://github.com/settings/tokens/new?scopes=repo&description=interview-coach-push

echo.
echo BUOC 2: Dan TOKEN vao day (trong terminal van dan duoc)
echo         Token bat dau bang ghp_ ...
echo.
set /p GITHUB_TOKEN=Nhap token: 

if "%GITHUB_TOKEN%"=="" (
    echo [ERROR] Token trong.
    pause
    exit /b 1
)

echo %GITHUB_TOKEN%| "%GH%" auth login --with-token
if errorlevel 1 (
    echo [ERROR] Token khong hop le hoac het han.
    pause
    exit /b 1
)

echo.
echo Dang tao repo va push...
"%GH%" repo create interview-coach --public --source=. --remote=origin --push
if errorlevel 1 (
    echo.
    echo Neu repo da ton tai, thu:
    echo   git remote remove origin
    echo   git remote add origin https://github.com/YOUR_USERNAME/interview-coach.git
    echo   git push -u origin main
    pause
    exit /b 1
)

echo.
echo THANH CONG!
"%GH%" repo view --web
pause
