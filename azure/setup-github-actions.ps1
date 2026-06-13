#Requires -Version 5.1
param(
    [string]$ResourceGroup = "rg-interview-coach-jack0",
    [string]$AcrName = "ca57dcca1882acr",
    [string]$SpName = "github-interview-coach-deploy",
    [string]$Location = "westus2",
    [string]$ContainerAppsEnv = "ic-jack0-env"
)

$ErrorActionPreference = "Stop"
$az = Join-Path ${env:ProgramFiles} "Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
$outFile = Join-Path $PSScriptRoot "azure-credentials.json"

& $az account set --subscription "Azure for Students" | Out-Null
$subId = & $az account show --query id -o tsv
$tenantId = & $az account show --query tenantId -o tsv
$rgScope = "/subscriptions/$subId/resourceGroups/$ResourceGroup"
$acrScope = & $az acr show -n $AcrName -g $ResourceGroup --query id -o tsv

$appId = & $az ad sp list --filter "displayName eq '$SpName'" --query "[0].appId" -o tsv
if (-not $appId) {
    Write-Host "Creating service principal..."
    & $az ad sp create-for-rbac --name $SpName --role contributor --scopes $rgScope --only-show-errors | Out-Null
    $appId = & $az ad sp list --filter "displayName eq '$SpName'" --query "[0].appId" -o tsv
}

Write-Host "Resetting SP password..."
$secret = & $az ad sp credential reset --id $appId --query password -o tsv
& $az role assignment create --assignee $appId --role AcrPush --scope $acrScope --output none 2>$null

$creds = @{
    clientId       = $appId
    clientSecret   = $secret
    subscriptionId = $subId
    tenantId       = $tenantId
}
$creds | ConvertTo-Json | Set-Content $outFile -Encoding utf8

Write-Host ""
Write-Host "Saved: $outFile (DO NOT commit)"
Write-Host ""
Write-Host "GitHub Secrets to add:"
Write-Host "  AZURE_CREDENTIALS = contents of azure-credentials.json"
Write-Host "  ACR_NAME=$AcrName"
Write-Host "  AZURE_RG=$ResourceGroup"
Write-Host "  AZURE_LOCATION=$Location"
Write-Host "  CONTAINERAPPS_ENV=$ContainerAppsEnv"
Write-Host "  OPENAI_API_KEY=optional"
Write-Host ""
Write-Host "Then: Actions -> Deploy to Azure Container Apps -> Run workflow"
