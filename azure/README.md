# Deploy Interview Coach backend to Azure Container Apps

## Docker local khong dung duoc?

Neu Docker Desktop bao **"Virtualization support not detected"**:
- Can bat **Virtualization / VT-x / AMD-V** trong BIOS (hoac lien he IT admin truong)
- **Khong can Docker local** — dung **GitHub Actions** (build tren cloud) xem muc duoi

## Deploy khuyen nghi: GitHub Actions (khong can Docker)

Subscription: **Azure for Students** | Region: **westus2**

### Buoc 1 — Azure da san sang

| Tai nguyen | Gia tri |
|------------|---------|
| Resource group | `rg-interview-coach-jack0` |
| Container Apps env | `ic-jack0-env` (westus2) |
| ACR | `ca57dcca1882acr` |

```powershell
$env:Path = "${env:ProgramFiles}\Microsoft SDKs\Azure\CLI2\wbin;" + $env:Path
az account set --subscription "Azure for Students"
cd azure
.\setup-github-actions.ps1
```

### Buoc 2 — GitHub Secrets

Repo: `jack060305-design/Multimodal-AI-Interview-Coach`  
Settings → Secrets and variables → Actions:

| Secret | Gia tri |
|--------|---------|
| `AZURE_CREDENTIALS` | JSON tu `setup-github-actions.ps1` |
| `ACR_NAME` | `ca57dcca1882acr` |
| `AZURE_RG` | `rg-interview-coach-jack0` |
| `AZURE_LOCATION` | `westus2` |
| `CONTAINERAPPS_ENV` | `ic-jack0-env` |
| `OPENAI_API_KEY` | key OpenAI (Whisper + agentic) |

### Buoc 3 — Chay workflow

Actions → **Deploy to Azure Container Apps** → **Run workflow**

Hoac push len `main` (tu dong deploy khi doi backend/rubrics).

### Buoc 4 — Vercel

Lay URL tu workflow summary hoac:

```powershell
az containerapp show -g rg-interview-coach-jack0 -n interview-coach-api --query properties.configuration.ingress.fqdn -o tsv
```

Dat `NEXT_PUBLIC_API_URL=https://<fqdn>` tren Vercel.

---

## Kien truc LangGraph Multi-Agent

```
Vercel (frontend)
       │
       ▼
Azure Container App (FastAPI, min replicas 0–1)
       │
       ├── POST /evaluate, /interview/...  (Whisper + LangGraph interview agents)
       │
       └── Azure Files mount → /app/backend/data
             ├── llm_daily_questions.json   (cache câu hỏi agentic)
             └── question_feed_cache.json   (feed GitHub)

Azure Container Apps Job (cron 06:00 UTC) — khuyến nghị cho sinh viên
       │
       └── python jobs/run_daily_questions.py
             └── LangGraph daily pipeline:
                   Planner (1 LLM)
                     → Researcher (0 LLM, đọc cache)
                     → Generator (4 LLM, 1/role)
                     → Critic (1 LLM batch)
                     → [optional 1 vòng revision]
```

### Chi phí LLM / ngày (agentic, 4 roles × 3 câu)

| Agent | LLM calls | Ghi chú |
|-------|-----------|---------|
| Planner | 1 | Kế hoạch theme + góc role |
| Researcher | 0 | Đọc feed cache + bank |
| Generator | 4 | 1 call/role |
| Critic | 1–2 | Batch review + optional revision |
| **Tổng** | **6–11** | `gpt-4o-mini` ≈ vài cent/ngày |

### Chi phí Azure (gợi ý tiết kiệm)

| Tài nguyên | Cấu hình gợi ý | Lý do |
|------------|----------------|-------|
| Container App API | 0.5 vCPU, 1Gi, **min=0** | Scale-to-zero khi không ai luyện tập |
| Container Apps Job | 0.5 vCPU, 1Gi, 1 lần/ngày | Cron agentic, ~2–5 phút/chạy |
| Azure Files | 1 GB | Cache câu hỏi bền vững |
| ACR Basic | 1 registry | Build image |

> **Lưu ý:** `min replicas=0` → cold start ~10–30s cho request đầu. Nếu demo thường xuyên, đặt `min=1`.

## Yêu cầu

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) (`az login`)
- Subscription Azure for Students đã kích hoạt
- `OPENAI_API_KEY`

## Biến môi trường

Xem `containerapp.env.example`.

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `DAILY_QUESTIONS_MODE` | `agentic` | `agentic` = LangGraph 4 agent; `simple` = 1 LLM/role |
| `DAILY_QUESTIONS_MAX_REVISIONS` | `1` | Vòng critic → generator tối đa |
| `DAILY_QUESTIONS_PER_ROLE` | `3` | Câu mới/role/ngày |
| `LLM_MODEL` | `gpt-4o-mini` | Đủ tốt, rẻ cho agentic |

## Deploy (PowerShell)

```powershell
cd azure
.\deploy.ps1 `
  -ResourceGroup "rg-interview-coach" `
  -Location "southeastasia" `
  -AcrName "interviewcoachacr" `
  -OpenAiApiKey "sk-..." `
  -CorsOrigins "https://multimodal-ai-interview-coach.vercel.app" `
  -CreateDailyJob `
  -MinReplicas 0
```

Khi dùng **Container Apps Job** (khuyến nghị), tắt cron trong API container:

```
DAILY_QUESTIONS_ENABLED=false   # trên Container App API
DAILY_QUESTIONS_ENABLED=true    # trên Container Apps Job
```

## Sau deploy

1. URL API:
   ```powershell
   az containerapp show -g rg-interview-coach -n interview-coach-api `
     --query properties.configuration.ingress.fqdn -o tsv
   ```
2. Vercel: `NEXT_PUBLIC_API_URL=https://<fqdn>`
3. Kiểm tra agentic pipeline:
   ```powershell
   curl "https://<fqdn>/questions/daily/status"
   curl -X POST "https://<fqdn>/questions/daily/run?force=true"
   ```

Response `/questions/daily/status` sẽ có:
- `mode: "agentic"`
- `agent_trace`: log Planner → Researcher → Generator → Critic
- `llm_calls_last_run`: số lần gọi LLM lần chạy gần nhất

## Chạy Job thủ công (debug)

```powershell
az containerapp job start -g rg-interview-coach -n interview-coach-api-daily
az containerapp job execution list -g rg-interview-coach -n interview-coach-api-daily -o table
```

## LangSmith (tùy chọn)

Bật tracing cho multi-agent graph:

```
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=interview-coach-daily-agents
```

## API endpoints

- `GET /questions/daily/status` — cache, theme, mode, agent_trace
- `POST /questions/daily/generate` — chạy LangGraph agentic
- `POST /questions/daily/run` — feed sync + agentic generation

## So sánh mode

| | `agentic` | `simple` |
|---|-----------|----------|
| LLM calls/ngày | 6–11 | 4 |
| Chất lượng | Cao (critic + research) | Cơ bản |
| Phù hợp Azure | Job cron 1 lần/ngày | APScheduler in-process |

## Phương án 2 (chưa triển khai)

Event-driven + RSS crawler — có thể gắn vào **Researcher agent** sau này mà không đổi graph.
