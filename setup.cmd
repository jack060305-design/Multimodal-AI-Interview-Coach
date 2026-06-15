@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Node.js (winget) — available in new terminals; ensure setup.cmd finds npm
if exist "C:\Program Files\nodejs\npm.cmd" set "PATH=C:\Program Files\nodejs;%PATH%"

echo.
echo  ========================================
echo   Interview Coach - Local Setup
echo  ========================================
echo.
echo  Structure:
echo    rubrics/          questions + rubrics
echo    backend/main.py   API server
echo    backend/processors/  video + speech
echo    backend/evaluator.py scoring
echo    frontend/         web UI
echo.
echo  Online: https://multimodal-ai-interview-coach.vercel.app
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Install Python 3.11+ from python.org
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Install Node.js from nodejs.org
    pause
    exit /b 1
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [WARN] ffmpeg missing. Install: winget install Gyan.FFmpeg
    echo.
)

echo [1/4] Rubrics + backend...
if not exist "backend\.venv" python -m venv backend\.venv

call backend\.venv\Scripts\activate.bat
pip install -r backend\requirements.txt -q
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

if not exist "backend\.env" (
    copy /Y backend\.env.example backend\.env >nul
    echo       Created backend\.env ^(SQLite login DB — see backend/.env.example^)
) else (
    python "%~dp0scripts\ensure-backend-env.py"
)

rem Clear stale shell overrides so backend/.env wins (load_dotenv override=True)
set DB_ENABLED=
set DEPLOY_PROFILE=

pushd backend
python ingest_rubrics.py
if errorlevel 1 (
    echo [ERROR] rubrics/sample_rubrics.py ingest failed.
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

echo [3/4] Start API (main.py) + UI...
start "Interview Coach - Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"
start "Interview Coach - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo [4/4] Open browser...
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
echo [WARN] Open manually: http://localhost:3000

:done
echo.
echo  Ready
echo    Web : http://localhost:3000
echo    API : http://127.0.0.1:8000
echo    Login: http://localhost:3000/login
echo    Health: http://127.0.0.1:8000/health  ^(db_connected should be true^)
echo.
pause
