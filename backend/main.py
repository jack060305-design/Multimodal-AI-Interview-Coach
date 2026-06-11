import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from db.database import get_db, init_db
from db.repository import EvaluationRepository
from schemas import EvaluationHistoryItem, EvaluationResult, GpuConsentRequest, Role
from services.orchestrator import EvaluationOrchestrator
from tracing.langsmith_setup import configure_langsmith
from utils.device import accelerator_status_dict, hardware_status_dict, log_accelerator_profile
from utils.gpu_consent import clear_stored_consent, consent_status, resolve_consent, save_stored_consent

load_dotenv()
logging.basicConfig(level=logging.INFO)
configure_langsmith()

orchestrator: EvaluationOrchestrator | None = None
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    log_accelerator_profile()
    init_db()
    orchestrator = EvaluationOrchestrator()
    yield


app = FastAPI(
    title="Interview Coach API",
    description=(
        "Multimodal AI interview coaching: video/audio/transcript analysis "
        "with Whisper, MediaPipe, OpenCV, librosa, and RAG-grounded LLM rubric scoring."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "vector_store": settings.vector_store,
        "storage_backend": settings.storage_backend,
        "db_enabled": settings.db_enabled,
        "langsmith": settings.langsmith_enabled,
        "accelerator": accelerator_status_dict(),
        "gpu": hardware_status_dict(),
    }


@app.get("/gpu/status")
async def gpu_status():
    return hardware_status_dict()


@app.post("/gpu/consent")
async def set_gpu_consent(body: GpuConsentRequest):
    choice = body.choice.lower()
    if choice == "always":
        save_stored_consent("always")
    elif choice == "never":
        save_stored_consent("never")
    elif choice == "reset":
        clear_stored_consent()
    else:
        raise HTTPException(400, "choice must be always, never, or reset")
    return {**hardware_status_dict(), **consent_status()}


@app.get("/roles")
async def list_roles():
    return {
        "roles": [
            {"id": Role.SWE_INTERN.value, "label": "SWE Intern"},
            {"id": Role.DATA_ANALYST.value, "label": "Data Analyst"},
            {"id": Role.FINANCE_ANALYST.value, "label": "Finance Analyst"},
            {"id": Role.PRODUCT_MANAGER.value, "label": "Product Manager"},
        ]
    }


@app.get("/questions/{role}")
async def list_questions(role: Role):
    from rubrics.sample_rubrics import SAMPLE_RUBRICS

    questions = [
        {"question_id": r.question_id, "question": r.question}
        for r in SAMPLE_RUBRICS
        if r.role == role
    ]
    return {"role": role.value, "questions": questions}


@app.get("/evaluations", response_model=list[EvaluationHistoryItem])
async def list_evaluations(limit: int = 20):
    db = get_db()
    if db is None:
        return []
    try:
        records = EvaluationRepository(db).list_recent(limit=limit)
        return [
            EvaluationHistoryItem(
                evaluation_id=r.id,
                role=Role(r.role),
                question_id=r.question_id,
                question=r.question,
                overall_score=r.overall_score,
                delivery_score=r.delivery_score,
                communication_score=r.communication_score,
                technical_score=r.technical_score,
                created_at=r.created_at.isoformat(),
                video_storage_key=r.video_storage_key,
            )
            for r in records
        ]
    finally:
        db.close()


@app.get("/evaluations/{evaluation_id}", response_model=EvaluationResult)
async def get_evaluation(evaluation_id: UUID):
    db = get_db()
    if db is None:
        raise HTTPException(503, "Database not available")
    try:
        record = EvaluationRepository(db).get(evaluation_id)
        if not record:
            raise HTTPException(404, "Evaluation not found")
        return EvaluationResult.model_validate(record.result_json)
    finally:
        db.close()


@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate(
    role: Role = Form(...),
    question: str = Form(...),
    question_id: str | None = Form(None),
    gpu_consent: str | None = Form(None),
    video: UploadFile = File(...),
):
    if orchestrator is None:
        raise HTTPException(503, "Service not ready")

    if not video.filename:
        raise HTTPException(400, "Video file required")

    content = await video.read()
    if len(content) == 0:
        raise HTTPException(400, "Empty video file")

    hw = hardware_status_dict()
    consent = (gpu_consent or "").strip().lower() or None
    if hw["gpu_available"] and resolve_consent(consent) == "unset":
        raise HTTPException(
            428,
            detail={
                "message": "GPU consent required before using hardware acceleration.",
                "gpu_name": hw.get("gpu_name"),
                "choices": ["once", "always", "never"],
            },
        )

    try:
        return orchestrator.evaluate_upload(
            file_bytes=content,
            filename=video.filename,
            role=role,
            question=question,
            question_id=question_id,
            gpu_consent=consent,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Evaluation failed: {e}") from e


@app.websocket("/ws/evaluation-progress")
async def evaluation_progress(websocket: WebSocket):
    """Optional real-time progress channel (WebRTC-adjacent streaming UX)."""
    await websocket.accept()
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Submit video via POST /evaluate. Progress events coming soon.",
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
