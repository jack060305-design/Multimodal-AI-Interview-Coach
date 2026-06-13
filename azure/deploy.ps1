#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy Interview Coach FastAPI backend to Azure Container Apps.

.EXAMPLE
  .\deploy.ps1 -ResourceGroup rg-interview-coach -Location southeastasia `
    -AcrName interviewcoachacr -OpenAiApiKey "sk-..." `
    -CorsOrigins "https://multimodal-ai-interview-coach.vercel.app"
#>
param(
    [string]$ResourceGroup = "rg-interview-coach",
    [string]$Location = "southeastasia",
    [string]$AcrName = "interviewcoachacr",
    [string]$AppName = "interview-coach-api",
    [string]$EnvironmentName = "interview-coach-env",
    [string]$StorageAccountName = "icquestioncache",
    [string]$FileShareName = "question-data",
    [string]$OpenAiApiKey = "",
    [string]$CorsOrigins = "http://localhost:3000",
    [int]$MinReplicas = 0,
    [switch]$CreateDailyJob,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Require-Az {
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw "Azure CLI (az) is required. Install: https://learn.microsoft.com/cli/azure/install-azure-cli"
    }
    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        throw "Run 'az login' first."
    }
}

Require-Az

Write-Host "==> Resource group: $ResourceGroup ($Location)"
az group create --name $ResourceGroup --location $Location --output none

Write-Host "==> Container Registry: $AcrName"
$acrExists = $null
try {
    $acrExists = az acr show --name $AcrName --resource-group $ResourceGroup 2>$null
} catch {
    $acrExists = $null
}
if (-not $acrExists) {
    az acr create --resource-group $ResourceGroup --name $AcrName --sku Basic --admin-enabled true --output none
}

$acrLoginServer = az acr show --name $AcrName --resource-group $ResourceGroup --query loginServer -o tsv
$imageTag = "${acrLoginServer}/interview-coach:latest"

if (-not $SkipBuild) {
    Write-Host "==> Building and pushing image: $imageTag"
    az acr build --registry $AcrName --image interview-coach:latest --file "$RepoRoot/Dockerfile.cloud" $RepoRoot
}

Write-Host "==> Log Analytics + Container Apps Environment"
$workspaceId = az monitor log-analytics workspace create `
    --resource-group $ResourceGroup `
    --workspace-name "${AppName}-logs" `
    --location $Location `
    --query id -o tsv

az containerapp env create `
    --name $EnvironmentName `
    --resource-group $ResourceGroup `
    --location $Location `
    --logs-workspace-id $workspaceId `
    --output none 2>$null

Write-Host "==> Storage account + file share for question cache"
az storage account create `
    --name $StorageAccountName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku Standard_LRS `
    --output none 2>$null

$storageKey = az storage account keys list `
    --resource-group $ResourceGroup `
    --account-name $StorageAccountName `
    --query "[0].value" -o tsv

az storage share create `
    --name $FileShareName `
    --account-name $StorageAccountName `
    --account-key $storageKey `
    --output none 2>$null

$acrPassword = az acr credential show --name $AcrName --query "passwords[0].value" -o tsv

Write-Host "==> Deploying Container App: $AppName (min replicas=$MinReplicas)"
$apiSchedulerEnabled = if ($CreateDailyJob) { "false" } else { "true" }
$envVars = @(
    "DEPLOY_PROFILE=cloud",
    "WHISPER_BACKEND=openai",
    "VECTOR_STORE=memory",
    "LLM_PROVIDER=openai",
    "LLM_MODEL=gpt-4o-mini",
    "DB_ENABLED=false",
    "DAILY_QUESTIONS_ENABLED=$apiSchedulerEnabled",
    "DAILY_QUESTIONS_MODE=agentic",
    "DAILY_QUESTIONS_CRON=0 6 * * *",
    "DAILY_QUESTIONS_PER_ROLE=3",
    "DAILY_QUESTIONS_MAX_REVISIONS=1",
    "CORS_ORIGINS=$CorsOrigins",
    "WORK_DIR=/tmp/interview-work",
    "LOCAL_STORAGE_DIR=/tmp/interview-uploads"
)
$jobEnvVars = @(
    "DEPLOY_PROFILE=cloud",
    "WHISPER_BACKEND=openai",
    "VECTOR_STORE=memory",
    "LLM_PROVIDER=openai",
    "LLM_MODEL=gpt-4o-mini",
    "DB_ENABLED=false",
    "DAILY_QUESTIONS_ENABLED=true",
    "DAILY_QUESTIONS_MODE=agentic",
    "DAILY_QUESTIONS_PER_ROLE=3",
    "DAILY_QUESTIONS_MAX_REVISIONS=1",
    "WORK_DIR=/tmp/interview-work",
    "LOCAL_STORAGE_DIR=/tmp/interview-uploads"
)
if ($OpenAiApiKey) {
    $envVars += "OPENAI_API_KEY=$OpenAiApiKey"
    $jobEnvVars += "OPENAI_API_KEY=$OpenAiApiKey"
}

$envArg = ($envVars | ForEach-Object { $_ }) -join " "

az containerapp create `
    --name $AppName `
    --resource-group $ResourceGroup `
    --environment $EnvironmentName `
    --image $imageTag `
    --registry-server $acrLoginServer `
    --registry-username $AcrName `
    --registry-password $acrPassword `
    --target-port 8000 `
    --ingress external `
    --min-replicas $MinReplicas `
    --max-replicas 2 `
    --cpu 0.5 `
    --memory 1.0Gi `
    --env-vars $envVars `
    --output none 2>$null

if ($LASTEXITCODE -ne 0) {
    az containerapp update `
        --name $AppName `
        --resource-group $ResourceGroup `
        --image $imageTag `
        --set-env-vars $envVars `
        --output none
}

Write-Host "==> Mount Azure Files at /app/backend/data"
az containerapp env storage set `
    --name $EnvironmentName `
    --resource-group $ResourceGroup `
    --storage-name questioncache `
    --azure-file-account-name $StorageAccountName `
    --azure-file-account-key $storageKey `
    --azure-file-share-name $FileShareName `
    --access-mode ReadWrite `
    --output none 2>$null

az containerapp update `
    --name $AppName `
    --resource-group $ResourceGroup `
    --set-env-vars "DEPLOY_PROFILE=cloud" `
    --output none

# Note: volume mount syntax varies by CLI version; document manual step if needed
Write-Host ""
Write-Host "If cache mount fails via CLI, add in Azure Portal:"
Write-Host "  Container -> Volume mount: questioncache -> /app/backend/data"
Write-Host ""

$fqdn = az containerapp show --name $AppName --resource-group $ResourceGroup --query "properties.configuration.ingress.fqdn" -o tsv

if ($CreateDailyJob) {
    Write-Host "==> Container Apps Job (agentic daily pipeline at 06:00 UTC)"
    az containerapp job create `
        --name "${AppName}-daily" `
        --resource-group $ResourceGroup `
        --environment $EnvironmentName `
        --trigger-type Schedule `
        --cron-expression "0 6 * * *" `
        --replica-timeout 900 `
        --replica-retry-limit 2 `
        --parallelism 1 `
        --replica-completion-count 1 `
        --image $imageTag `
        --registry-server $acrLoginServer `
        --registry-username $AcrName `
        --registry-password $acrPassword `
        --cpu 0.5 `
        --memory 1.0Gi `
        --command "python" `
        --args "jobs/run_daily_questions.py" `
        --env-vars $jobEnvVars `
        --output none 2>$null

    if ($LASTEXITCODE -ne 0) {
        az containerapp job update `
            --name "${AppName}-daily" `
            --resource-group $ResourceGroup `
            --image $imageTag `
            --set-env-vars $jobEnvVars `
            --output none
    }
}

Write-Host ""
Write-Host "Deploy complete."
Write-Host "API URL: https://$fqdn"
Write-Host "Health:  https://$fqdn/health"
Write-Host "Daily:   https://$fqdn/questions/daily/status"
Write-Host ""
Write-Host "Set on Vercel: NEXT_PUBLIC_API_URL=https://$fqdn"
