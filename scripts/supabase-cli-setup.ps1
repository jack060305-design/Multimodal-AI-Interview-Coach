#Requires -Version 5.1
<#
  Supabase CLI setup (run in repo root):
    1. npx supabase login          # browser — complete in terminal
    2. npx supabase init           # already done if supabase/config.toml exists
    3. npx supabase link --project-ref ttgdcomdfqmbqqiywoxw
#>

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "=== 1/3 supabase login ===" -ForegroundColor Cyan
Write-Host "A browser window will open. Approve access, then return here."
npx supabase login
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== 2/3 supabase init ===" -ForegroundColor Cyan
if (Test-Path "supabase\config.toml") {
  Write-Host "Already initialized (supabase/config.toml exists). Skipping."
} else {
  npx supabase init --yes
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "`n=== 3/3 supabase link ===" -ForegroundColor Cyan
Write-Host "You may be prompted for your database password (from Supabase project creation)."
npx supabase link --project-ref ttgdcomdfqmbqqiywoxw
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nDone. Project linked to ttgdcomdfqmbqqiywoxw." -ForegroundColor Green
Write-Host "Next: set GOOGLE_OAUTH_CLIENT_ID/SECRET and run scripts/setup-supabase-google.ps1 for cloud Google OAuth."
