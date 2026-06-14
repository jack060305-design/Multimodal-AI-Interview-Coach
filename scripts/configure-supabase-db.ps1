#Requires -Version 5.1
<#
.SYNOPSIS
  Point local API at Supabase Postgres (optional — default local uses SQLite).

.USAGE
  $env:SUPABASE_DB_PASSWORD = "<Supabase Dashboard -> Database -> Settings>"
  .\scripts\configure-supabase-db.ps1

  Then restart the backend (close API terminal or re-run setup.cmd).
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$EnvFile = Join-Path $Root "backend\.env"
$Password = $env:SUPABASE_DB_PASSWORD
$Project = if ($env:SUPABASE_PROJECT_REF) { $env:SUPABASE_PROJECT_REF } else { "ttgdcomdfqmbqqiywoxw" }

if (-not $Password) {
    Write-Host "Set SUPABASE_DB_PASSWORD first (Supabase Dashboard -> Database -> Settings)." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $Root "backend\.env.example") $EnvFile
}

$lines = Get-Content $EnvFile | Where-Object { $_ -notmatch '^\s*SUPABASE_DB_PASSWORD=' }
$lines += "SUPABASE_DB_PASSWORD=$Password"
$lines += "DB_ENABLED=true"
Set-Content -Path $EnvFile -Value ($lines | Select-Object -Unique)

Write-Host "Updated backend\.env with SUPABASE_DB_PASSWORD." -ForegroundColor Green
Write-Host "Restart API, then check: http://127.0.0.1:8000/health -> db_backend=postgres, db_connected=true"
