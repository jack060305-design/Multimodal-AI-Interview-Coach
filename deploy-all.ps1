#Requires -Version 5.1
param(
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$RepoUrl = "https://github.com/jack060305-design/Multimodal-AI-Interview-Coach"
$ServiceName = "interview-coach-api"
$BackendUrl = "https://interview-coach-api.onrender.com"

function Load-DotEnv([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line -match "^([^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            if (-not [string]::IsNullOrWhiteSpace($val)) {
                Set-Item -Path "env:$key" -Value $val
            }
        }
    }
}

function Invoke-RenderApi {
    param([string]$Method, [string]$Uri, [object]$Body = $null)
    $headers = @{
        Authorization = "Bearer $env:RENDER_API_KEY"
        Accept        = "application/json"
    }
    if ($Body) {
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 10)
    }
    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers
}

Write-Host "============================================================"
Write-Host " AUTO DEPLOY: Render backend + Vercel proxy (Full AI)"
Write-Host "============================================================"
Write-Host ""

Load-DotEnv (Join-Path $Root "deploy\secrets.env")
Load-DotEnv (Join-Path $Root "backend\.env")

if (-not $SkipPush) {
    Write-Host "[1/4] Push config len GitHub..."
    git add render.yaml deploy-all.ps1 deploy-all.cmd deploy/secrets.env.example .gitignore 2>$null
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git -c user.email="jack060305-design@users.noreply.github.com" -c user.name="jack060305-design" `
            commit -m "Add render.yaml root + auto deploy script for full AI online"
        git push origin main
    } else {
        git push origin main 2>$null
    }
    Write-Host "      OK - Vercel se tu deploy lai frontend"
}

if (-not $env:RENDER_API_KEY) {
    Write-Host ""
    Write-Host "[2/4] Chua co RENDER_API_KEY - mo Render Blueprint (1 lan)..."
    $blueprint = "https://dashboard.render.com/blueprint/new?repo=$([uri]::EscapeDataString($RepoUrl))"
    Start-Process $blueprint
    Write-Host ""
    Write-Host "  Trong trinh duyet:"
    Write-Host "  - Dang nhap GitHub (neu can)"
    Write-Host "  - Blueprint path: render.yaml (root)"
    Write-Host "  - Them OPENAI_API_KEY"
    Write-Host "  - Bam Deploy Blueprint"
    Write-Host ""
    Write-Host "  Lay RENDER_API_KEY tai: https://dashboard.render.com/u/settings#api-keys"
    Write-Host "  Luu vao: deploy\secrets.env (xem secrets.env.example)"
    Write-Host ""
    Write-Host "[3/4] Doi backend khoi dong..."
} else {
    Write-Host "[2/4] Deploy backend len Render qua API..."

    $owners = Invoke-RenderApi GET "https://api.render.com/v1/owners"
    $ownerId = $owners[0].owner.id

    $existing = $null
    try {
        $services = Invoke-RenderApi GET "https://api.render.com/v1/services?limit=100"
        $existing = $services | ForEach-Object { $_.service } | Where-Object { $_.name -eq $ServiceName } | Select-Object -First 1
    } catch { }

    $envVars = @(
        @{ key = "LLM_PROVIDER"; value = "openai" },
        @{ key = "LLM_MODEL"; value = "gpt-4o-mini" },
        @{ key = "VECTOR_STORE"; value = "chroma" },
        @{ key = "STORAGE_BACKEND"; value = "local" },
        @{ key = "DB_ENABLED"; value = "false" },
        @{ key = "CORS_ORIGINS"; value = "http://localhost:3000,https://multimodal-ai-interview-coach.vercel.app" }
    )
    if ($env:OPENAI_API_KEY -and $env:OPENAI_API_KEY -notmatch "sk-\.\.\.|your_openai") {
        $envVars += @{ key = "OPENAI_API_KEY"; value = $env:OPENAI_API_KEY }
    }

    if (-not $existing) {
        $body = @{
            type    = "web_service"
            name    = $ServiceName
            ownerId = $ownerId
            repo    = $RepoUrl
            branch  = "main"
            serviceDetails = @{
                env              = "docker"
                plan             = "free"
                region           = "oregon"
                healthCheckPath  = "/health"
                dockerfilePath   = "./Dockerfile"
                envSpecificDetails = @{
                    dockerCommand = ""
                }
                envVars = $envVars
            }
        }
        $created = Invoke-RenderApi POST "https://api.render.com/v1/services" $body
        Write-Host "      Tao service: $($created.service.name)"
    } else {
        Write-Host "      Service da ton tai - trigger deploy..."
        Invoke-RenderApi POST "https://api.render.com/v1/services/$($existing.id)/deploys" @{ clearCache = "do_not_clear" } | Out-Null
    }

    Write-Host "[3/4] Doi backend san sang..."
}

$maxWait = 600
$elapsed = 0
$healthy = $false
while ($elapsed -lt $maxWait) {
    try {
        $r = Invoke-WebRequest -Uri "$BackendUrl/health" -TimeoutSec 20 -UseBasicParsing
        if ($r.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch { }
    Write-Host "      ... dang cho ($elapsed s / $maxWait s)"
    Start-Sleep -Seconds 15
    $elapsed += 15
}

Write-Host ""
Write-Host "[4/4] Kiem tra ket noi..."
if ($healthy) {
    try {
        $roles = Invoke-RestMethod -Uri "$BackendUrl/roles" -TimeoutSec 20
        Write-Host "      Backend OK - $($roles.roles.Count) roles"
    } catch {
        Write-Host "      Backend health OK nhung /roles chua san sang"
    }
    Write-Host ""
    Write-Host "============================================================"
    Write-Host " FULL AI ONLINE"
    Write-Host " Backend: $BackendUrl"
    Write-Host " Frontend Vercel: https://multimodal-ai-interview-coach.vercel.app"
    Write-Host " (Vercel proxy /roles, /evaluate -> Render)"
    Write-Host "============================================================"
} else {
    Write-Host ""
    Write-Host "Backend chua len sau $maxWait giay."
    Write-Host "Render free tier co the mat 5-10 phut lan dau."
    Write-Host "Kiem tra: $BackendUrl/health"
    Write-Host "Sau do refresh trang Vercel."
}
