# Interview Coach

AI mock interview app: record a video answer, get scores for **delivery**, **communication**, and **technical depth**.

## Live demo (no install)

**https://multimodal-ai-interview-coach.vercel.app**

Use the site in your browser. Roles and questions load from the page. Full video analysis needs the local app (below).

---

## Run on your computer (full AI)

### What you need

| Tool | Install |
|------|---------|
| Python 3.11+ | [python.org](https://www.python.org/downloads/) |
| Node.js 20+ | [nodejs.org](https://nodejs.org/) |
| ffmpeg | `winget install Gyan.FFmpeg` |

### Start (Windows)

Double-click **`setup.cmd`** or run:

```cmd
setup.cmd
```

This will:

1. Install Python and Node dependencies  
2. Start the API on port **8000**  
3. Start the web app on port **3000**  
4. Open **http://localhost:3000**

Close the two black terminal windows to stop.

### How to use the app

1. Pick a **role** and **question**  
2. **Record** your answer  
3. Click **Submit for Evaluation**  
4. Read scores and feedback on the right  

No OpenAI key required by default (`LLM_PROVIDER=local` in `backend/.env`). For GPT scoring, set `LLM_PROVIDER=openai` and add `OPENAI_API_KEY`.

---

## Project layout

```
interview-coach/
├── frontend/     Next.js UI (also on Vercel)
├── backend/      FastAPI + Whisper + video/audio analysis
├── rubrics/      Interview questions and scoring rubrics
├── setup.cmd     Start everything locally (Windows)
└── vercel.json   Vercel deploy config
```

---

## Optional

**Docker (Postgres + MinIO + full stack)**

```cmd
copy backend\.env.example backend\.env
docker compose up --build
```

**GPU** — Works on CPU by default. NVIDIA or AMD extras: see comments in `backend/.env.example`.

**API docs** — After local start: http://127.0.0.1:8000/docs

| Endpoint | Purpose |
|----------|---------|
| `GET /roles` | List roles |
| `GET /questions/{role}` | Questions for a role |
| `POST /evaluate` | Upload video, get scores |

---

## License

MIT
