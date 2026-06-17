#Requires -Version 5.1
<#
.SYNOPSIS
  Facebook Login via Backend OAuth (Meta Graph API — Plan B).

.USAGE
  1. Create Meta App at https://developers.facebook.com
  2. Add Facebook Login product
  3. Set env vars and run this script to patch backend/.env + frontend/.env.local

  $env:FACEBOOK_APP_ID = "<Meta App ID>"
  $env:FACEBOOK_APP_SECRET = "<Meta App Secret>"
  .\scripts\setup-facebook-backend-oauth.ps1

  Optional:
  $env:PUBLIC_API_URL = "http://localhost:8000"   # default local
  $env:FRONTEND_URL = "http://localhost:3000"
#>

$ErrorActionPreference = "Stop"

$Root = Split-Path $PSScriptRoot -Parent
$BackendEnv = Join-Path $Root "backend\.env"
$FrontendEnv = Join-Path $Root "frontend\.env.local"
$FrontendExample = Join-Path $Root "frontend\.env.local.example"

$AppId = $env:FACEBOOK_APP_ID
$AppSecret = $env:FACEBOOK_APP_SECRET
$ApiUrl = if ($env:PUBLIC_API_URL) { $env:PUBLIC_API_URL.TrimEnd("/") } else { "http://localhost:8000" }
$RedirectUri = "$ApiUrl/auth/facebook/callback"

Write-Host ""
Write-Host "=== Facebook Backend OAuth (Meta Graph API) ===" -ForegroundColor Cyan
Write-Host "Redirect URI (add in Meta App): $RedirectUri"
Write-Host ""

if (-not $AppId -or -not $AppSecret) {
  Write-Host "MISSING: FACEBOOK_APP_ID / FACEBOOK_APP_SECRET" -ForegroundColor Red
  Write-Host "  1. https://developers.facebook.com/apps/"
  Write-Host "  2. Create App -> Consumer or Business"
  Write-Host "  3. Add product: Facebook Login"
  Write-Host "  4. Facebook Login -> Settings -> Valid OAuth Redirect URIs:"
  Write-Host "       $RedirectUri"
  Write-Host "  5. App Review not needed for email + public_profile in dev mode"
  Write-Host "  6. Add test users under Roles -> Test Users (dev mode)"
  Write-Host ""
  exit 1
}

function Set-EnvKey {
  param([string]$Path, [string]$Key, [string]$Value)
  if (-not (Test-Path $Path)) { return }
  $lines = Get-Content $Path -ErrorAction SilentlyContinue
  $found = $false
  $out = foreach ($line in $lines) {
    if ($line -match "^\s*$([regex]::Escape($Key))=") {
      $found = $true
      "$Key=$Value"
    } else { $line }
  }
  if (-not $found) { $out += "$Key=$Value" }
  $out | Set-Content $Path -Encoding utf8
  Write-Host "  $Path -> $Key" -ForegroundColor Green
}

if (-not (Test-Path $BackendEnv)) {
  Copy-Item (Join-Path $Root "backend\.env.example") $BackendEnv
}

Set-EnvKey $BackendEnv "FACEBOOK_APP_ID" $AppId
Set-EnvKey $BackendEnv "FACEBOOK_APP_SECRET" $AppSecret
Set-EnvKey $BackendEnv "FACEBOOK_REDIRECT_URI" $RedirectUri
Set-EnvKey $BackendEnv "PUBLIC_API_URL" $ApiUrl

if (-not (Test-Path $FrontendEnv)) {
  if (Test-Path $FrontendExample) {
    Copy-Item $FrontendExample $FrontendEnv
  }
}
Set-EnvKey $FrontendEnv "NEXT_PUBLIC_BACKEND_FACEBOOK_OAUTH" "true"
Set-EnvKey $FrontendEnv "NEXT_PUBLIC_API_URL" $ApiUrl

Write-Host ""
Write-Host "Done. Restart setup.cmd (backend + frontend) then test:" -ForegroundColor Cyan
Write-Host "  http://localhost:3000/login -> Facebook icon"
Write-Host "  Health: $ApiUrl/health  (facebook_oauth should be true)"
Write-Host ""
