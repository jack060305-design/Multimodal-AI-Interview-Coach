#Requires -Version 5.1
<#
.SYNOPSIS
  Enable Google OAuth on Supabase project ttgdcomdfqmbqqiywoxw via Management API.

.USAGE
  $env:SUPABASE_ACCESS_TOKEN = "<from https://supabase.com/dashboard/account/tokens>"
  $env:GOOGLE_OAUTH_CLIENT_ID = "<Google Cloud OAuth Client ID>"
  $env:GOOGLE_OAUTH_CLIENT_SECRET = "<Google Cloud OAuth Client Secret>"
  .\scripts\setup-supabase-google.ps1

  Optional:
  $env:SUPABASE_PROJECT_REF = "ttgdcomdfqmbqqiywoxw"   # default
  $env:SUPABASE_SITE_URL = "https://multimodal-ai-interview-coach.vercel.app"
#>

$ErrorActionPreference = "Stop"

$ProjectRef = if ($env:SUPABASE_PROJECT_REF) { $env:SUPABASE_PROJECT_REF } else { "ttgdcomdfqmbqqiywoxw" }
$SiteUrl = if ($env:SUPABASE_SITE_URL) { $env:SUPABASE_SITE_URL } else { "https://multimodal-ai-interview-coach.vercel.app" }
$Token = $env:SUPABASE_ACCESS_TOKEN
$GoogleId = $env:GOOGLE_OAUTH_CLIENT_ID
$GoogleSecret = $env:GOOGLE_OAUTH_CLIENT_SECRET

$RedirectUrls = @(
  "http://localhost:3000/auth/callback",
  "http://127.0.0.1:3000/auth/callback",
  "$SiteUrl/auth/callback"
) -join ","

$SupabaseCallback = "https://$ProjectRef.supabase.co/auth/v1/callback"

Write-Host ""
Write-Host "=== Supabase Google OAuth Setup ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectRef"
Write-Host "Supabase callback (add in Google Cloud): $SupabaseCallback"
Write-Host ""

if (-not $Token) {
  Write-Host "MISSING: SUPABASE_ACCESS_TOKEN" -ForegroundColor Red
  Write-Host "  1. Open https://supabase.com/dashboard/account/tokens"
  Write-Host "  2. Generate token -> set env SUPABASE_ACCESS_TOKEN"
  Write-Host ""
}
if (-not $GoogleId -or -not $GoogleSecret) {
  Write-Host "MISSING: GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET" -ForegroundColor Red
  Write-Host "  1. Open https://console.cloud.google.com/apis/credentials"
  Write-Host "  2. Create OAuth 2.0 Client ID (Web application)"
  Write-Host "  3. Authorized redirect URI: $SupabaseCallback"
  Write-Host "  4. Copy Client ID + Secret into env vars"
  Write-Host ""
}

if (-not $Token -or -not $GoogleId -or -not $GoogleSecret) {
  Write-Host "Re-run after setting all three environment variables." -ForegroundColor Yellow
  exit 1
}

$headers = @{
  Authorization = "Bearer $Token"
  "Content-Type" = "application/json"
}

$body = @{
  external_google_enabled = $true
  external_google_client_id = $GoogleId
  external_google_secret = $GoogleSecret
  site_url = $SiteUrl
  uri_allow_list = $RedirectUrls
} | ConvertTo-Json

Write-Host "Patching Supabase auth config..." -ForegroundColor Cyan
try {
  $response = Invoke-RestMethod `
    -Method PATCH `
    -Uri "https://api.supabase.com/v1/projects/$ProjectRef/config/auth" `
    -Headers $headers `
    -Body $body

  Write-Host "OK Google OAuth enabled on Supabase." -ForegroundColor Green
  Write-Host "  site_url: $SiteUrl"
  Write-Host "  redirect URLs: $RedirectUrls"
}
catch {
  Write-Host "API error: $($_.Exception.Message)" -ForegroundColor Red
  if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
  exit 1
}

Write-Host ""
Write-Host "=== Google OAuth consent screen (DeepSeek-style branding) ===" -ForegroundColor Cyan
Write-Host "  1. https://console.cloud.google.com/auth/branding"
Write-Host "     App name: Multimodal AI Interview Coach"
Write-Host "     Upload logo (square PNG)"
Write-Host "     Authorized domains: vercel.app (and your domain if you add one later)"
Write-Host "  2. https://console.cloud.google.com/apis/credentials"
Write-Host "     OAuth client (Web) -> Authorized JavaScript origins:"
Write-Host "       http://localhost:3000"
Write-Host "       $SiteUrl"
Write-Host "     (Redirect URI for Supabase backend flow: $SupabaseCallback)"
Write-Host "  3. Supabase -> Auth -> Providers -> Google:"
Write-Host "     Same Client ID, enable 'Skip nonce check' for GIS / signInWithIdToken"
Write-Host "  4. Vercel env: NEXT_PUBLIC_GOOGLE_CLIENT_ID=<Web client ID>"
Write-Host "     Users will see 'Continue to $SiteUrl' instead of *.supabase.co"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Test: http://localhost:3000/login -> click Google icon"
Write-Host "  2. Add GitHub Secrets (Azure backend saves users to Postgres):"
Write-Host "       SUPABASE_URL=https://$ProjectRef.supabase.co"
Write-Host "       SUPABASE_JWT_SECRET=<Settings -> API -> JWT Secret>"
Write-Host "       DATABASE_URL=<Settings -> Database -> connection string>"
Write-Host ""
