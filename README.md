# Interview Coach

AI mock interview app: record a video answer, get scores for **delivery**, **communication**, and **technical depth**.

## Live demo (no install)

**https://multimodal-ai-interview-coach.vercel.app** (login: `/login`)

If `/login` shows 404, use the latest preview: **https://multimodal-ai-interview-coach-yf5s.vercel.app/login**

---

## Run on your computer (full AI)

| Tool | Install |
|------|---------|
| Python 3.11+ | [python.org](https://www.python.org/downloads/) |
| Node.js 20+ | [nodejs.org](https://nodejs.org/) |
| ffmpeg | `winget install Gyan.FFmpeg` |

```cmd
setup.cmd
```

Opens **http://localhost:3000** (API on port **8000**). Close the two terminal windows to stop.

### How to use

1. Pick **role** + **question**  
2. **Record** your answer  
3. **Submit for Evaluation**  
4. Read scores on the right  

Default: local AI scoring (no OpenAI key). For GPT: `LLM_PROVIDER=openai` + `OPENAI_API_KEY` in `backend/.env`.

---

## Project structure

Core layout (main files):

```
interview-coach/
├── backend/
│   ├── main.py              # FastAPI entry
│   ├── schemas.py           # API models
│   ├── evaluator.py         # Rubric / LLM scoring
│   ├── vector_store.py      # RAG rubric retrieval
│   ├── requirements.txt
│   └── processors/
│       ├── video_processor.py
│       └── transcriber.py
├── rubrics/
│   └── sample_rubrics.py
├── Dockerfile
└── README.md
```

Also in this repo (not shown above):

```
├── frontend/          # Next.js UI (Vercel)
├── setup.cmd          # Start local app (Windows)
├── vercel.json        # Vercel deploy
├── docker-compose.yml
└── backend/           # more modules: config, workflows,
                        # rubric_engine/, db/, services/, …
```

### Processing order

```
video upload
  → processors/     (ffmpeg, Whisper, CV, audio)
  → vector_store    (find rubric)
  → evaluator       (score answer)
  → JSON response
```

---

## API (local)

http://127.0.0.1:8000/docs

| Endpoint | Purpose |
|----------|---------|
| `GET /roles` | List roles |
| `GET /questions/{role}` | Questions |
| `POST /evaluate` | Upload video → scores |

---

## Optional

```cmd
copy backend\.env.example backend\.env
docker compose up --build
```

GPU / Postgres / S3: see `backend/.env.example`.

---

## License

MIT
