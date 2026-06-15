#Requires -Version 5.1
<#
.SYNOPSIS
  Dual auth: Firebase (Google login) + Supabase (email + Postgres).

.USAGE
  1. Create Firebase project + Web app at https://console.firebase.google.com
  2. Enable Authentication -> Google provider
  3. Set env vars below, then run this script to enable Supabase third-party Firebase

  $env:SUPABASE_ACCESS_TOKEN = "<from https://supabase.com/dashboard/account/tokens>"
  $env:FIREBASE_PROJECT_ID = "<your-firebase-project-id>"
  .\scripts\setup-firebase-supabase.ps1
#>

$ErrorActionPreference = "Stop"

$ProjectRef = if ($env:SUPABASE_PROJECT_REF) { $env:SUPABASE_PROJECT_REF } else { "ttgdcomdfqmbqqiywoxw" }
$SiteUrl = if ($env:SUPABASE_SITE_URL) { $env:SUPABASE_SITE_URL } else { "https://multimodal-ai-interview-coach.vercel.app" }
$Token = $env:SUPABASE_ACCESS_TOKEN
$FirebaseProjectId = $env:FIREBASE_PROJECT_ID

Write-Host ""
Write-Host "=== Firebase + Supabase dual auth ===" -ForegroundColor Cyan
Write-Host "Firebase: Google sign-in (branded account picker)"
Write-Host "Supabase: email/password + Postgres + third-party Firebase JWT"
Write-Host ""

if (-not $FirebaseProjectId) {
  Write-Host "MISSING: FIREBASE_PROJECT_ID" -ForegroundColor Red
  Write-Host "  Firebase Console -> Project settings -> Project ID"
  Write-Host ""
}

if (-not $Token) {
  Write-Host "MISSING: SUPABASE_ACCESS_TOKEN (optional — enables third-party Firebase on Supabase)" -ForegroundColor Yellow
  Write-Host "  https://supabase.com/dashboard/account/tokens"
  Write-Host ""
}

Write-Host "=== 1/4 Firebase Console ===" -ForegroundColor Cyan
Write-Host "  https://console.firebase.google.com"
Write-Host "  - Add Web app -> copy firebaseConfig (apiKey, authDomain, projectId, appId)"
Write-Host "  - Authentication -> Sign-in method -> Google -> Enable"
Write-Host "  - Authentication -> Settings -> Authorized domains:"
Write-Host "      localhost"
Write-Host "      $SiteUrl.Replace('https://','')"
Write-Host "  - Google Cloud OAuth consent screen: app name + logo (branding)"
Write-Host ""

Write-Host "=== 2/4 Frontend .env.local ===" -ForegroundColor Cyan
Write-Host @"
NEXT_PUBLIC_FIREBASE_API_KEY=<from firebaseConfig>
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=<project>.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=$FirebaseProjectId
NEXT_PUBLIC_FIREBASE_APP_ID=<from firebaseConfig>

# Supabase (email + DB) — keep existing:
NEXT_PUBLIC_SUPABASE_URL=https://$ProjectRef.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=...
"@
Write-Host ""

Write-Host "=== 3/4 Backend backend/.env ===" -ForegroundColor Cyan
Write-Host "FIREBASE_PROJECT_ID=$FirebaseProjectId"
Write-Host "(same value as NEXT_PUBLIC_FIREBASE_PROJECT_ID)"
Write-Host ""

if ($Token -and $FirebaseProjectId) {
  $headers = @{
    Authorization = "Bearer $Token"
    "Content-Type" = "application/json"
  }
  $body = @{
    third_party_firebase_enabled = $true
    third_party_firebase_project_id = $FirebaseProjectId
  } | ConvertTo-Json

  Write-Host "=== 4/4 Enable Supabase third-party Firebase ===" -ForegroundColor Cyan
  try {
    Invoke-RestMethod `
      -Method PATCH `
      -Uri "https://api.supabase.com/v1/projects/$ProjectRef/config/auth" `
      -Headers $headers `
      -Body $body | Out-Null
    Write-Host "OK Supabase third-party Firebase enabled for project $FirebaseProjectId." -ForegroundColor Green
  }
  catch {
    Write-Host "API patch failed (enable manually in Dashboard):" -ForegroundColor Yellow
    Write-Host "  Supabase -> Authentication -> Third-party Auth -> Firebase"
    Write-Host "  Project ID: $FirebaseProjectId"
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
  }
}
else {
  Write-Host "=== 4/4 Supabase third-party Firebase ===" -ForegroundColor Cyan
  Write-Host "  Manual: Dashboard -> Authentication -> Third-party Auth -> Firebase"
  Write-Host "  Project ID: $FirebaseProjectId"
}

Write-Host ""
Write-Host "=== Vercel / Azure ===" -ForegroundColor Cyan
Write-Host "  Vercel: all NEXT_PUBLIC_FIREBASE_* + Supabase vars"
Write-Host "  Azure GitHub Secret: FIREBASE_PROJECT_ID=$FirebaseProjectId"
Write-Host ""
Write-Host "Test: npm run dev -> http://localhost:3000/login -> Google icon (Firebase popup)" -ForegroundColor Green
Write-Host ""
