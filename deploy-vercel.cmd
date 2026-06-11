@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo  TU DONG CAU HINH + DEPLOY VERCEL
echo ============================================================
echo.

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Can cai Node.js
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    pushd frontend
    call npm install
    popd
)

echo Buoc 1: Dang nhap Vercel (mo trinh duyet, chon GitHub)...
start https://vercel.com/api/registration/login-with-github?mode=login
pushd frontend
call npx vercel login
if errorlevel 1 (
    echo Login that bai.
    popd
    pause
    exit /b 1
)

echo.
echo Buoc 2: Link project + set env tu dong...
call npx vercel link --yes --project multimodal-ai-interview-coach 2>nul
if errorlevel 1 (
    call npx vercel link --yes
)

echo http://localhost:8000| call npx vercel env add NEXT_PUBLIC_API_URL production preview development 2>nul

echo.
echo Buoc 3: Deploy production...
call npx vercel --prod --yes --name multimodal-ai-interview-coach
set EXIT=%ERRORLEVEL%
popd

if %EXIT% neq 0 (
    echo Deploy that bai.
    pause
    exit /b %EXIT%
)

echo.
echo ============================================================
echo  XONG! Frontend da len Vercel.
echo  Backend van chay local: setup.cmd
echo ============================================================
pause
