# Interview Coach

Multimodal AI interview coaching platform that analyzes **video, audio, and transcript** signals using Whisper, MediaPipe, OpenCV, librosa, and **LLM-based RAG rubric evaluation** to generate structured feedback across **delivery**, **communication**, and **technical depth**.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, Tailwind, webcam video recorder |
| Backend | FastAPI |
| STT | faster-whisper (Whisper) |
| CV | MediaPipe Face Landmarker + OpenCV |
| Audio | librosa (pitch, RMS, WPM, pauses) |
| LLM | GPT-4o mini / Claude / Gemini |
| RAG | LangChain + Chroma or Pinecone |
| Database | PostgreSQL (evaluation history) |
| Storage | Local filesystem or S3 (MinIO/AWS) |
| Orchestration | LangGraph multimodal pipeline |
| Tracing | LangSmith (optional) |
| Deployment | Docker Compose, Render blueprint |

## Architecture

```
Record video (Next.js)
  → Upload POST /evaluate
  → LangGraph pipeline:
      ffmpeg → Whisper → MediaPipe CV → librosa audio
      → RAG retrieve rubric (Chroma/Pinecone)
      → LLM grounded scoring (OpenAI/Anthropic/Gemini)
  → Performance pillars: Delivery | Communication | Technical Depth
  → Persist: Postgres + S3/local storage
```

## Quick Start (Windows)

```cmd
setup.cmd
```

Opens http://localhost:3000 automatically.

### Prerequisites

- Python 3.11+, Node.js 20+
- ffmpeg: `winget install Gyan.FFmpeg`
- `OPENAI_API_KEY` in `backend\.env`

### GPU (optional — safe on every machine)

Default **`ACCELERATOR_MODE=auto`**: uses NVIDIA CUDA when available, otherwise CPU. **No GPU required** — machines without CUDA never crash.

| Mode | Behavior |
|------|----------|
| `auto` | GPU if CUDA detected, else CPU (default) |
| `cpu` | Force CPU (laptops, CI, low-spec machines) |
| `gpu` | Prefer GPU, **fall back to CPU** if unavailable |

```env
ACCELERATOR_MODE=auto
WHISPER_DEVICE=auto
WHISPER_COMPUTE=auto
EMBEDDING_DEVICE=auto
```

Check runtime profile:

```cmd
cd backend
.venv\Scripts\activate.bat
python scripts\check_gpu.py
```

**GPU machine only** (optional extras):

```cmd
pip install -r requirements-gpu.txt
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

`GET /health` returns `accelerator` with `using_gpu`, `whisper_device`, etc.

### AMD Radeon (RX 6700 XT, RX 7900, …)

Windows + AMD uses **DirectML** (not CUDA). Auto-detects Radeon via WMI, or set manually:

```env
GPU_VENDOR=amd
AMD_GPU_NAME=RX 6700 XT
WHISPER_BACKEND=onnx_directml
```

```cmd
pip install -r requirements-amd.txt
python scripts\check_gpu.py
```

| Component | AMD path |
|-----------|----------|
| Whisper STT | ONNX + DirectML (`onnx_directml`) |
| RAG embeddings | `torch-directml` |
| No DirectML installed | CPU fallback (no crash) |

Machines without AMD/NVIDIA still use `GPU_VENDOR=auto` → CPU.

### GPU consent (required before acceleration)

GPU is **never used until the user allows it**:

| Choice | Behavior |
|--------|----------|
| **Just once** | GPU for current evaluation only |
| **Always** | Saved in browser + server (`data/gpu_consent.json`) |
| **CPU only** | Never use GPU on this machine |

- Web app shows a modal on first submit if GPU is detected
- `setup.cmd` asks the same question when starting the project
- `GET /gpu/status` — check if prompt is required
- `POST /gpu/consent` — `{ "choice": "always" | "never" | "reset" }`

## Docker (full stack)

Includes **Postgres**, **MinIO (S3)**, backend, and production-built frontend:

```cmd
copy backend\.env.example backend\.env
docker compose up --build
```

- Web UI: http://localhost:3000
- API: http://localhost:8000
- MinIO console: http://localhost:9001 (minio / minio12345)

## Configuration (`backend/.env`)

```env
# LLM: openai | anthropic | gemini
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# Vector store: chroma | pinecone
VECTOR_STORE=chroma

# Storage: local | s3
STORAGE_BACKEND=local

# Postgres
DATABASE_URL=postgresql+psycopg2://interview:interview@localhost:5432/interview_coach

# LangSmith (optional)
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=...
```

See `backend/.env.example` for all variables.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service status + config |
| GET | `/roles` | Available interview roles |
| GET | `/questions/{role}` | Questions per role |
| POST | `/evaluate` | Multimodal evaluation (multipart video) |
| GET | `/evaluations` | Evaluation history (Postgres) |
| GET | `/evaluations/{id}` | Single evaluation result |
| WS | `/ws/evaluation-progress` | Real-time progress channel |

## Production Deploy

- **Render**: `deploy/render.yaml`
- **Docker prod overlay**: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up`
- Set `VECTOR_STORE=pinecone`, `STORAGE_BACKEND=s3`, external Postgres + S3 credentials

## Project Structure

```
interview-coach/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── workflows/langgraph_pipeline.py
│   ├── processors/          # video, whisper, CV, audio
│   ├── rubric_engine/       # Chroma + Pinecone RAG
│   ├── db/                    # Postgres models
│   ├── storage/               # S3 + local
│   └── tracing/               # LangSmith
├── frontend/                  # Next.js recorder + results
├── deploy/render.yaml
├── docker-compose.yml
└── setup.cmd
```

## License

MIT
