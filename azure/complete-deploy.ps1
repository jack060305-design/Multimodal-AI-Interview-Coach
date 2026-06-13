#Requires -Version 5.1
# One-click deploy: GitHub Actions build (cloud) + Azure Container Apps.
# Requires: gh auth login (browser) once, azure-credentials.json from setup-github-actions.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$CredsFile = Join-Path $PSScriptRoot "azure-credentials.json"

function Ensure-GhAuth {
    gh auth status 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { return }
    Write-Host "Mo trinh duyet GitHub de dang nhap gh CLI..."
    Start-Process "https://github.com/login/device"
    gh auth login -h github.com -p https -w -s repo,workflow
    if ($LASTEXITCODE -ne 0) { throw "GitHub login failed. Chay: gh auth login -w -s repo,workflow" }
}

function Set-GhSecrets {
    if (-not (Test-Path $CredsFile)) {
        & (Join-Path $PSScriptRoot "setup-github-actions.ps1")
    }
    gh secret set AZURE_CREDENTIALS --repo jack060305-design/Multimodal-AI-Interview-Coach --body (Get-Content $CredsFile -Raw)
    gh secret set ACR_NAME --repo jack060305-design/Multimodal-AI-Interview-Coach --body "ca57dcca1882acr"
    gh secret set AZURE_RG --repo jack060305-design/Multimodal-AI-Interview-Coach --body "rg-interview-coach-jack0"
    gh secret set AZURE_LOCATION --repo jack060305-design/Multimodal-AI-Interview-Coach --body "westus2"
    gh secret set CONTAINERAPPS_ENV --repo jack060305-design/Multimodal-AI-Interview-Coach --body "ic-jack0-env"
    $envFile = Join-Path $RepoRoot "backend\.env"
    if (Test-Path $envFile) {
        foreach ($line in Get-Content $envFile) {
            if ($line -match '^OPENAI_API_KEY=(.+)$') {
                $key = $matches[1].Trim().Trim('"')
                if ($key.Length -gt 10) {
                    gh secret set OPENAI_API_KEY --repo jack060305-design/Multimodal-AI-Interview-Coach --body $key
                }
            }
        }
    }
    Write-Host "GitHub secrets configured."
}

Write-Host "==> GitHub auth"
Ensure-GhAuth

Write-Host "==> Set secrets"
Set-GhSecrets

Write-Host "==> Trigger deploy workflow"
gh workflow run "Deploy to Azure Container Apps" --repo jack060305-design/Multimodal-AI-Interview-Coach --ref main
Start-Sleep -Seconds 5
$runId = gh run list --repo jack060305-design/Multimodal-AI-Interview-Coach --workflow "Deploy to Azure Container Apps" --limit 1 --json databaseId -q ".[0].databaseId"
Write-Host "Watching run $runId (5-10 min)..."
gh run watch $runId --repo jack060305-design/Multimodal-AI-Interview-Coach --exit-status

$env:Path = "${env:ProgramFiles}\Microsoft SDKs\Azure\CLI2\wbin;" + $env:Path
az account set --subscription "Azure for Students" | Out-Null
$fqdn = az containerapp show -g rg-interview-coach-jack0 -n interview-coach-api --query "properties.configuration.ingress.fqdn" -o tsv 2>$null

Write-Host ""
Write-Host "=========================================="
Write-Host "DEPLOY THANH CONG"
Write-Host "=========================================="
Write-Host "API URL:  https://$fqdn"
Write-Host "Health:   https://$fqdn/health"
Write-Host "Daily:    https://$fqdn/questions/daily/status"
Write-Host ""
Write-Host "Vercel: NEXT_PUBLIC_API_URL=https://$fqdn"
Write-Host ""

try {
    $health = Invoke-RestMethod -Uri "https://$fqdn/health" -TimeoutSec 60
    Write-Host "Health check:"
    $health | ConvertTo-Json -Depth 4
} catch {
    Write-Host "Health check (cold start, thu lai sau 30s): $($_.Exception.Message)"
}
