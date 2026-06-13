#Requires -Version 5.1
# Set GitHub Actions secrets for LLM / tracing (paste keys when prompted).
param(
    [string]$Repo = "jack060305-design/Multimodal-AI-Interview-Coach"
)

$ErrorActionPreference = "Stop"

function Set-SecretIfProvided {
    param([string]$Name, [string]$Value)
    if ($Value) {
        $Value | gh secret set $Name --repo $Repo
        Write-Host "  OK $Name"
    }
}

Write-Host "GitHub repo: $Repo"
Write-Host "Leave blank to skip a secret."
Write-Host ""

$anthropic = Read-Host "ANTHROPIC_API_KEY (console.anthropic.com)"
$google = Read-Host "GOOGLE_API_KEY (aistudio.google.com)"
$openai = Read-Host "OPENAI_API_KEY (platform.openai.com — Whisper on cloud)"
$langsmith = Read-Host "LANGSMITH_API_KEY (smith.langchain.com)"

Set-SecretIfProvided "ANTHROPIC_API_KEY" $anthropic.Trim()
Set-SecretIfProvided "GOOGLE_API_KEY" $google.Trim()
Set-SecretIfProvided "OPENAI_API_KEY" $openai.Trim()
Set-SecretIfProvided "LANGSMITH_API_KEY" $langsmith.Trim()

Write-Host ""
Write-Host "Optional: repo Variables (Settings -> Actions -> Variables)"
Write-Host "  LLM_PROVIDER = anthropic | gemini | openai (auto if unset)"
Write-Host "  LLM_MODEL    = override default model"
Write-Host ""
Write-Host "Redeploy:"
Write-Host "  gh workflow run `"Deploy to Azure Container Apps`" --repo $Repo"
