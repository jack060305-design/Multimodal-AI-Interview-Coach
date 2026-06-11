@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo  DEPLOY FRONTEND LEN VERCEL
echo ============================================================
echo.
echo QUAN TRONG: Root Directory phai la "frontend" (khong phai ./)
echo.

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Can cai Node.js: https://nodejs.org
    pause
    exit /b 1
)

if not exist "frontend\node_modules\vercel" (
    echo Dang cai Vercel CLI...
    pushd frontend
    call npm install
    popd
)

pushd frontend
call .\node_modules\.bin\vercel.cmd whoami >nul 2>&1
if errorlevel 1 (
    echo Chua dang nhap Vercel. Mo trinh duyet de login GitHub...
    start https://vercel.com/api/registration/login-with-github?mode=login
    call npx vercel login
    if errorlevel 1 (
        echo.
        echo Login that bai. Dung Vercel Dashboard:
        echo   1. https://vercel.com/new
        echo   2. Import: jack060305-design/Multimodal-AI-Interview-Coach
        echo   3. Project Name: multimodal-ai-interview-coach
        echo   4. Root Directory: frontend  ^<-- BAT BUOC
        echo   5. Env: NEXT_PUBLIC_API_URL = http://localhost:8000
        echo   6. Deploy
        start https://vercel.com/new
        popd
        pause
        exit /b 1
    )
)

echo Dang deploy production...
call npx vercel --prod --yes --name multimodal-ai-interview-coach
set DEPLOY_EXIT=%ERRORLEVEL%
popd

if %DEPLOY_EXIT% neq 0 (
    echo [ERROR] Deploy that bai.
    pause
    exit /b %DEPLOY_EXIT%
)

echo.
echo DEPLOY XONG! Set NEXT_PUBLIC_API_URL trong Vercel Dashboard neu chua co.
pause
