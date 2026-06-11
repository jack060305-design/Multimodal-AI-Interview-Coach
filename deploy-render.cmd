@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo  DEPLOY BACKEND AI (Render) - can thiet cho Vercel full AI
echo ============================================================
echo.
echo Frontend Vercel se proxy API qua Render backend.
echo.

start https://dashboard.render.com/select-repo?type=blueprint
echo.
echo Buoc 1: Render Dashboard -^> New Blueprint
echo Buoc 2: Chon repo: Multimodal-AI-Interview-Coach
echo Buoc 3: Blueprint path: deploy/render.yaml
echo Buoc 4: Them OPENAI_API_KEY trong Environment
echo Buoc 5: Deploy - doi ~10 phut
echo.
echo Backend URL: https://interview-coach-api.onrender.com
echo.
pause
