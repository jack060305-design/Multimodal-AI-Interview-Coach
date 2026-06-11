@echo off
setlocal EnableExtensions
cd /d "%~dp0\frontend"

echo ============================================================
echo  DEPLOY FRONTEND LEN VERCEL
echo ============================================================
echo.
echo Luu y: Backend FastAPI chay rieng (Render/Railway/local).
echo       Sau khi deploy, set NEXT_PUBLIC_API_URL trong Vercel Dashboard.
echo.

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Can cai Node.js
    pause
    exit /b 1
)

echo Cach 1 - GitHub ^(khuyen dung, khong can CLI^):
echo   1. Vao https://vercel.com/new
echo   2. Import repo: jack060305-design/Multimodal-AI-Interview-Coach
echo   3. Root Directory: frontend
echo   4. Environment: NEXT_PUBLIC_API_URL = URL backend cua ban
echo   5. Deploy
echo.
echo Cach 2 - Vercel CLI:
echo   npx vercel login
echo   npx vercel --prod
echo.
set /p RUNCLI=Chay Vercel CLI ngay? [y/N]: 
if /i not "%RUNCLI%"=="y" (
    start https://vercel.com/new
    pause
    exit /b 0
)

call npm install
call npx vercel login
if errorlevel 1 (
    echo Login that bai. Dung Cach 1 ^(GitHub import^).
    start https://vercel.com/new
    pause
    exit /b 1
)

call npx vercel --prod
pause
