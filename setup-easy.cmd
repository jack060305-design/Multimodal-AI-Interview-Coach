@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo  ============================================================
echo   INTERVIEW COACH - SETUP TU DONG (1 buoc duy nhat)
echo  ============================================================
echo.
echo  Ban can 1 OpenAI API key de AI cham diem (mien phi dang ky).
echo  Lay tai: https://platform.openai.com/api-keys
echo.
start https://platform.openai.com/api-keys
echo.
set /p OPENAI_KEY="Dan OpenAI API key vao day (bat dau bang sk-): "

if "%OPENAI_KEY%"=="" (
    echo [LOI] Chua dan key. Chay lai setup-easy.cmd
    pause
    exit /b 1
)

echo.
echo [1/5] Luu cau hinh...
(
    echo OPENAI_API_KEY=%OPENAI_KEY%
    echo LLM_PROVIDER=openai
    echo LLM_MODEL=gpt-4o-mini
    echo WHISPER_MODEL=base
    echo WHISPER_DEVICE=cpu
    echo WHISPER_COMPUTE=int8
    echo CHROMA_PERSIST_DIR=./data/chroma
    echo WORK_DIR=./data/work
    echo DB_ENABLED=false
    echo CORS_ORIGINS=http://localhost:3000,https://multimodal-ai-interview-coach.vercel.app
) > backend\.env

echo NEXT_PUBLIC_API_URL=http://localhost:8000> frontend\.env.local

if not exist "deploy" mkdir deploy
(
    echo OPENAI_API_KEY=%OPENAI_KEY%
) > deploy\secrets.env

echo [2/5] Cai backend Python...
if not exist "backend\.venv" python -m venv backend\.venv
call backend\.venv\Scripts\activate.bat
pip install -r backend\requirements.txt -q
if errorlevel 1 (
    echo [LOI] Cai Python that bai
    pause
    exit /b 1
)

echo [3/5] Nap rubric AI...
pushd backend
python ingest_rubrics.py
popd

echo [4/5] Cai frontend...
pushd frontend
if not exist "node_modules" call npm install
popd

echo [5/5] Khoi dong server...
start "Backend AI" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"
timeout /t 3 /nobreak >nul
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo  Doi 10 giay roi mo trinh duyet...
timeout /t 10 /nobreak >nul
start http://localhost:3000

echo.
echo  ============================================================
echo   XONG! Full AI chay tai: http://localhost:3000
echo   - Chon Role + Question
echo   - Quay video -^> Submit for Evaluation
echo.
echo   De len Vercel online: chay deploy-all.cmd
echo   (OpenAI key da luu san trong deploy\secrets.env)
echo  ============================================================
echo.
pause
