#!/bin/bash
# Run in Azure Cloud Shell (https://shell.azure.com) — has Docker, no local virtualization needed.
set -euo pipefail

RG="rg-interview-coach-jack0"
LOCATION="westus2"
ACR="ca57dcca1882acr"
ENV_NAME="ic-jack0-env"
APP_NAME="interview-coach-api"
JOB_NAME="interview-coach-api-daily"
IMAGE="$ACR.azurecr.io/interview-coach:latest"
REPO="https://github.com/jack060305-design/Multimodal-AI-Interview-Coach.git"

echo "==> Subscription"
az account set --subscription "Azure for Students"

echo "==> Clone repo"
rm -rf /tmp/interview-coach
git clone --depth 1 "$REPO" /tmp/interview-coach
cd /tmp/interview-coach

echo "==> Build and push (Cloud Shell Docker)"
az acr login --name "$ACR"
docker build -f Dockerfile.cloud -t "$IMAGE" .
docker push "$IMAGE"

ACR_PASS=$(az acr credential show -n "$ACR" --query "passwords[0].value" -o tsv)

ENV_VARS=(
  "DEPLOY_PROFILE=cloud"
  "WHISPER_BACKEND=openai"
  "VECTOR_STORE=memory"
  "LLM_PROVIDER=openai"
  "LLM_MODEL=gpt-4o-mini"
  "DB_ENABLED=false"
  "DAILY_QUESTIONS_MODE=agentic"
  "DAILY_QUESTIONS_ENABLED=false"
  "DAILY_QUESTIONS_PER_ROLE=3"
  "DAILY_QUESTIONS_MAX_REVISIONS=1"
  "CORS_ORIGINS=http://localhost:3000,https://multimodal-ai-interview-coach.vercel.app"
  "WORK_DIR=/tmp/interview-work"
  "LOCAL_STORAGE_DIR=/tmp/interview-uploads"
)

if [ -n "${OPENAI_API_KEY:-}" ]; then
  ENV_VARS+=("OPENAI_API_KEY=$OPENAI_API_KEY")
fi

echo "==> Deploy Container App"
if az containerapp show -g "$RG" -n "$APP_NAME" &>/dev/null; then
  az containerapp update -g "$RG" -n "$APP_NAME" \
    --image "$IMAGE" \
    --set-env-vars "${ENV_VARS[@]}"
else
  az containerapp create -g "$RG" -n "$APP_NAME" \
    --environment "$ENV_NAME" \
    --image "$IMAGE" \
    --registry-server "$ACR.azurecr.io" \
    --registry-username "$ACR" \
    --registry-password "$ACR_PASS" \
    --target-port 8000 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 2 \
    --cpu 0.5 --memory 1.0Gi \
    --env-vars "${ENV_VARS[@]}"
fi

JOB_ENV=(
  "DEPLOY_PROFILE=cloud"
  "LLM_PROVIDER=openai"
  "LLM_MODEL=gpt-4o-mini"
  "DB_ENABLED=false"
  "DAILY_QUESTIONS_ENABLED=true"
  "DAILY_QUESTIONS_MODE=agentic"
  "DAILY_QUESTIONS_PER_ROLE=3"
)
[ -n "${OPENAI_API_KEY:-}" ] && JOB_ENV+=("OPENAI_API_KEY=$OPENAI_API_KEY")

echo "==> Deploy daily job"
if az containerapp job show -g "$RG" -n "$JOB_NAME" &>/dev/null; then
  az containerapp job update -g "$RG" -n "$JOB_NAME" --image "$IMAGE" --set-env-vars "${JOB_ENV[@]}"
else
  az containerapp job create -g "$RG" -n "$JOB_NAME" \
    --environment "$ENV_NAME" \
    --trigger-type Schedule \
    --cron-expression "0 6 * * *" \
    --replica-timeout 900 \
    --image "$IMAGE" \
    --registry-server "$ACR.azurecr.io" \
    --registry-username "$ACR" \
    --registry-password "$ACR_PASS" \
    --cpu 0.5 --memory 1.0Gi \
    --command "python" \
    --args "jobs/run_daily_questions.py" \
    --env-vars "${JOB_ENV[@]}"
fi

FQDN=$(az containerapp show -g "$RG" -n "$APP_NAME" --query "properties.configuration.ingress.fqdn" -o tsv)
echo ""
echo "Done!"
echo "API:    https://$FQDN"
echo "Health: https://$FQDN/health"
echo "Set Vercel: NEXT_PUBLIC_API_URL=https://$FQDN"
