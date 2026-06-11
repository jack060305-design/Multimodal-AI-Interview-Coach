@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [autorun] Interview Coach - zero interaction setup

(
    echo LLM_PROVIDER=local
    echo LLM_MODEL=local
    echo WHISPER_MODEL=base
    echo WHISPER_DEVICE=cpu
    echo WHISPER_COMPUTE=int8
    echo CHROMA_PERSIST_DIR=./data/chroma
    echo WORK_DIR=./data/work
    echo DB_ENABLED=false
    echo STORAGE_BACKEND=local
    echo CORS_ORIGINS=http://localhost:3000,https://multimodal-ai-interview-coach.vercel.app
) > backend\.env

echo NEXT_PUBLIC_API_URL=http://localhost:8000> frontend\.env.local

if not exist "backend\.venv" python -m venv backend\.venv
call backend\.venv\Scripts\activate.bat
pip install -r backend\requirements.txt -q

pushd backend
python ingest_rubrics.py
popd

pushd frontend
if not exist "node_modules" call npm install >nul 2>&1
popd

taskkill /FI "WINDOWTITLE eq Backend AI*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend*" /F >nul 2>&1

start "Backend AI" /MIN cmd /c "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000"
ping -n 5 127.0.0.1 >nul
start "Frontend" /MIN cmd /c "cd /d %~dp0frontend && npm run dev"
ping -n 9 127.0.0.1 >nul

start http://localhost:3000
start https://dashboard.render.com/blueprint/new?repo=https%%3A%%2F%%2Fgithub.com%%2Fjack060305-design%%2FMultimodal-AI-Interview-Coach

git -c user.email="jack060305-design@users.noreply.github.com" -c user.name="jack060305-design" commit --allow-empty -m "autorun: trigger redeploy" >nul 2>&1
git push origin main >nul 2>&1

echo [autorun] Done - http://localhost:3000
echo [autorun] Vercel redeploy triggered. Render blueprint opened (no API key needed).
