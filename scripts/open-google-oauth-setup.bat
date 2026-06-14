@echo off
REM Quick helper — opens Google Cloud + Supabase pages for OAuth setup
start https://console.cloud.google.com/apis/credentials?project=_ 
start https://supabase.com/dashboard/project/ttgdcomdfqmbqqiywoxw/auth/providers?provider=Google
start https://supabase.com/dashboard/project/ttgdcomdfqmbqqiywoxw/auth/url-configuration
start https://supabase.com/dashboard/account/tokens
echo.
echo Google Cloud: Create OAuth Client ID (Web)
echo   Redirect URI: https://ttgdcomdfqmbqqiywoxw.supabase.co/auth/v1/callback
echo.
echo Supabase: Paste Client ID + Secret on Google provider page
echo.
echo Or automate with PowerShell:
echo   set SUPABASE_ACCESS_TOKEN=your_token
echo   set GOOGLE_OAUTH_CLIENT_ID=your_client_id
echo   set GOOGLE_OAUTH_CLIENT_SECRET=your_secret
echo   powershell -File scripts\setup-supabase-google.ps1
echo.
