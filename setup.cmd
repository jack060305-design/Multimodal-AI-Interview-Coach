@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Interview Coach ===
echo.

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [WARN] ffmpeg not found in PATH. Install: winget install Gyan.FFmpeg
    echo.
)

echo [1/4] Backend setup...
if not exist "backend\.venv" (
    python -m venv backend\.venv
    if errorlevel 1 (
        echo [ERROR] Failed to create Python venv. Install Python 3.11+
        pause
        exit /b 1
    )
)

call backend\.venv\Scripts\activate.bat
pip install -r backend\requirements.txt -q
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)

if not exist "backend\.env" (
    copy /Y backend\.env.example backend\.env >nul
    echo Created backend\.env - add OPENAI_API_KEY before evaluating answers.
)

echo      DB_ENABLED=false in backend\.env if Postgres is not running locally.

pushd backend
echo.
echo [GPU] Checking accelerator (NVIDIA CUDA / AMD DirectML / CPU fallback)...
python scripts\check_gpu.py
if exist requirements-amd.txt (
    echo      AMD RX card? pip install -r requirements-amd.txt ^& set GPU_VENDOR=amd in .env
)
echo.
echo GPU consent for this machine:
echo   1 = Ask in web app each time ^(default^)
echo   2 = Always allow GPU
echo   3 = CPU only - never use GPU
set /p GPU_CONSENT_CHOICE="Choose [1/2/3] (default 1): "
if "%GPU_CONSENT_CHOICE%"=="2" (
    python -c "from utils.gpu_consent import save_stored_consent; save_stored_consent('always'); print('Saved: always allow GPU')"
) else if "%GPU_CONSENT_CHOICE%"=="3" (
    python -c "from utils.gpu_consent import save_stored_consent; save_stored_consent('never'); print('Saved: CPU only')"
) else (
    echo Will ask in web app before using GPU.
)
echo.
python ingest_rubrics.py
if errorlevel 1 (
    echo [ERROR] Rubric ingest failed
    popd
    pause
    exit /b 1
)
popd

echo.
echo [2/4] Frontend setup...
pushd frontend
if not exist "node_modules" (
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed
        popd
        pause
        exit /b 1
    )
)
if not exist ".env.local" (
    copy /Y .env.local.example .env.local >nul
)
popd

echo.
echo [3/4] Starting servers...
start "Interview Coach - Backend" cmd /k pushd "%~dp0backend" ^&^& call .venv\Scripts\activate.bat ^&^& uvicorn main:app --reload --port 8000
start "Interview Coach - Frontend" cmd /k pushd "%~dp0frontend" ^&^& npm run dev

echo.
echo [4/4] Waiting for frontend, then opening browser...
set /a RETRIES=0

:wait_frontend
set /a RETRIES+=1
if %RETRIES% GTR 30 (
    echo [WARN] Frontend slow to start. Open manually: http://localhost:3000
    goto done
)

powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:3000' -TimeoutSec 2).StatusCode | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto wait_frontend
)

start "" http://localhost:3000

:done
echo.
echo Ready!
echo   Web UI : http://localhost:3000
echo   API    : http://127.0.0.1:8000
echo.
echo Backend and frontend run in separate windows. Close those windows to stop.
pause
