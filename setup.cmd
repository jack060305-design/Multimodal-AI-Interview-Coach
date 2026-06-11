@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo  ========================================
echo   Interview Coach - Local Setup
echo  ========================================
echo.
echo  This installs dependencies and starts:
echo    Web app  -^> http://localhost:3000
echo    API      -^> http://127.0.0.1:8000
echo.
echo  Online demo: https://multimodal-ai-interview-coach.vercel.app
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install from nodejs.org
    pause
    exit /b 1
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [WARN] ffmpeg not in PATH. Install: winget install Gyan.FFmpeg
    echo.
)

echo [1/4] Backend...
if not exist "backend\.venv" (
    python -m venv backend\.venv
    if errorlevel 1 (
        echo [ERROR] Could not create Python virtual environment.
        pause
        exit /b 1
    )
)

call backend\.venv\Scripts\activate.bat
pip install -r backend\requirements.txt -q
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

if not exist "backend\.env" (
    copy /Y backend\.env.example backend\.env >nul
    echo       Created backend\.env (local AI mode, no API key needed).
)

pushd backend
python ingest_rubrics.py
if errorlevel 1 (
    echo [ERROR] Rubric setup failed.
    popd
    pause
    exit /b 1
)
popd

echo [2/4] Frontend...
pushd frontend
if not exist "node_modules" call npm install
if not exist ".env.local" copy /Y .env.local.example .env.local >nul
popd

echo [3/4] Starting servers (2 new windows)...
start "Interview Coach - Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"
start "Interview Coach - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo [4/4] Opening browser...
set /a RETRIES=0

:wait_frontend
set /a RETRIES+=1
if %RETRIES% GTR 30 goto open_manual

powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:3000' -TimeoutSec 2).StatusCode | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    ping -n 3 127.0.0.1 >nul
    goto wait_frontend
)

start "" http://localhost:3000
goto done

:open_manual
echo [WARN] Browser not opened automatically. Go to: http://localhost:3000

:done
echo.
echo  ========================================
echo   Ready
echo  ========================================
echo   Web:  http://localhost:3000
echo   API:  http://127.0.0.1:8000
echo.
echo   Close the Backend and Frontend windows to stop.
echo  ========================================
echo.
pause
