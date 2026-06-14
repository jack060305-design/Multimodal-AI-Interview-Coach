#Requires -Version 5.1
<#
.SYNOPSIS
  Configure Azure backend DATABASE_URL from Supabase Postgres password.

.USAGE
  $env:SUPABASE_DB_PASSWORD = "<from Supabase Dashboard -> Database -> Settings>"
  .\scripts\setup-azure-supabase-db.ps1

  Optional:
  $env:SUPABASE_PROJECT_REF = "ttgdcomdfqmbqqiywoxw"
  $env:GITHUB_REPO = "jack060305-design/Multimodal-AI-Interview-Coach"
#>

$ErrorActionPreference = "Stop"

$ProjectRef = if ($env:SUPABASE_PROJECT_REF) { $env:SUPABASE_PROJECT_REF } else { "ttgdcomdfqmbqqiywoxw" }
$Repo = if ($env:GITHUB_REPO) { $env:GITHUB_REPO } else { "jack060305-design/Multimodal-AI-Interview-Coach" }
$Password = $env:SUPABASE_DB_PASSWORD

if (-not $Password) {
  Write-Host "Set SUPABASE_DB_PASSWORD (Supabase Dashboard -> Database -> Settings -> Database password)." -ForegroundColor Red
  exit 1
}

$Encoded = [uri]::EscapeDataString($Password)
$DatabaseUrl = "postgresql://postgres:$Encoded@db.$ProjectRef.supabase.co:5432/postgres?sslmode=require"

$DatabaseUrl | gh secret set DATABASE_URL --repo $Repo
Write-Host "DATABASE_URL secret updated on GitHub ($Repo)." -ForegroundColor Green

Write-Host "Pushing schema to Supabase..."
Set-Location $PSScriptRoot\..
npx supabase db push --linked --yes
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Triggering Azure redeploy..."
gh workflow run "Deploy to Azure Container Apps" --repo $Repo
Write-Host "Done. Wait ~3 min, then check /health for db_enabled=true." -ForegroundColor Green
