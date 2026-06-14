# Verify login/database fixes locally — no git push required.
# Usage: .\scripts\verify-auth-fix.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "`n=== 1/4 Pytest (auth + database) ===" -ForegroundColor Cyan
Push-Location backend
python -m pytest tests/test_auth_db.py -v --tb=line
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "`n=== 2/4 Prepare local env (no git) ===" -ForegroundColor Cyan
if (-not (Test-Path "backend\.env")) {
    Copy-Item "backend\.env.example" "backend\.env"
    Write-Host "Created backend\.env from example"
}
if (-not (Test-Path "frontend\.env.local")) {
    Copy-Item "frontend\.env.local.example" "frontend\.env.local"
    Write-Host "Created frontend\.env.local from example"
}

# Local verify uses preview-auth-local.py (no forced DB_ENABLED=false)

Write-Host "`n=== 3/4 Start API briefly and probe /health + /auth/me ===" -ForegroundColor Cyan
$venvPython = "backend\.venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }
& $python (Join-Path $Root "scripts\preview-auth-local.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n(Skipped full uvicorn boot — use setup.cmd for login UI test)`n" -ForegroundColor DarkGray

Write-Host "`n=== 4/4 How to test login UI locally (manual) ===" -ForegroundColor Cyan
Write-Host @"

  Option A — one command (installs deps first time):
    setup.cmd
    Then open http://localhost:3000/login

  Option B — API only (already verified above):
    cd backend
    .\.venv\Scripts\activate   # or: python -m venv .venv && pip install -r requirements-cloud.txt
    uvicorn main:app --reload --port 8000

  To test WITH database (history saves):
    1. Supabase Dashboard -> Database -> copy password
    2. Edit backend\.env:
         DB_ENABLED=true
         DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.ttgdcomdfqmbqqiywoxw.supabase.co:5432/postgres?sslmode=require
         SUPABASE_URL=https://ttgdcomdfqmbqqiywoxw.supabase.co
    3. Restart API, login at http://localhost:3000/login
    4. curl http://127.0.0.1:8000/health  -> db_connected: true

  Cloud is unchanged until you git push — local is the preview of fixes.

"@ -ForegroundColor DarkGray

Write-Host "Done.`n" -ForegroundColor Green
