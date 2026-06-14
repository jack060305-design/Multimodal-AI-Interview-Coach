import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from auth import auth_router
from auth.deps import get_current_user, get_current_user_id_optional
from config import get_settings
from db.database import get_db, init_db
from db.models import User
from db.repository import EvaluationRepository
from schemas import (
    EvaluationHistoryItem,
    EvaluationResult,
    GpuConsentRequest,
    InterviewPreviewQuestionResponse,
    InterviewQuestionResponse,
    InterviewSessionCreate,
    InterviewSessionResponse,
    InterviewTurnRequest,
    InterviewTurnResponse,
    InterviewVideoTurnResponse,
    Role,
)
from services.interview_session_service import InterviewSessionService
from services.orchestrator import EvaluationOrchestrator
from services.question_feed_sync import maybe_sync_on_startup, sync_question_feed
from services.daily_question_scheduler import start_daily_scheduler, stop_daily_scheduler
from rubric_engine.bootstrap import bootstrap_vector_index
from storage.s3_bootstrap import ensure_s3_bucket
from tracing.langsmith_setup import configure_langsmith
from utils.device import accelerator_status_dict, hardware_status_dict, log_accelerator_profile
from utils.gpu_consent import clear_stored_consent, consent_status, resolve_consent, save_stored_consent

load_dotenv()
logging.basicConfig(level=logging.INFO)
configure_langsmith()

orchestrator: EvaluationOrchestrator | None = None
interview_service: InterviewSessionService | None = None
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator, interview_service
    log_accelerator_profile()
    init_db()
    ensure_s3_bucket()
    bootstrap_vector_index()
    maybe_sync_on_startup()
    start_daily_scheduler()
    orchestrator = EvaluationOrchestrator()
    interview_service = InterviewSessionService()
    yield
    stop_daily_scheduler()


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

app.include_router(auth_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "deploy_profile": settings.deploy_profile,
        "whisper_backend": settings.resolved_whisper_backend,
        "llm_provider": settings.llm_provider,
        "vector_store": settings.resolved_vector_store,
        "storage_backend": settings.storage_backend,
        "db_enabled": settings.db_enabled,
        "embedding_backend": settings.resolved_embedding_backend,
        "auth_enabled": settings.db_enabled,
        "supabase_auth": settings.supabase_enabled,
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


@app.get("/questions/feed/status")
async def question_feed_status():
    from rubrics.external_feed_loader import feed_status
    from workflows.interview_agents.question_bank import QUESTION_BANK, all_questions_for_role

    status = feed_status()
    status["bank_counts"] = {
        role: len(all_questions_for_role(role)) for role in QUESTION_BANK
    }
    return status


@app.post("/questions/feed/sync")
async def question_feed_sync(force: bool = False):
    try:
        return sync_question_feed(force=force)
    except Exception as exc:
        raise HTTPException(500, f"Feed sync failed: {exc}") from exc


@app.get("/questions/daily/status")
async def daily_questions_status():
    from services.daily_question_generator import llm_daily_status
    from workflows.interview_agents.question_bank import QUESTION_BANK, all_questions_for_role

    status = llm_daily_status()
    status["enabled"] = settings.daily_questions_enabled
    status["cron_utc"] = settings.daily_questions_cron
    status["per_role"] = settings.daily_questions_per_role
    status["mode"] = settings.daily_questions_mode
    status["max_revisions"] = settings.daily_questions_max_revisions
    status["agents"] = ["planner", "researcher", "generator", "critic"]
    status["bank_counts"] = {
        role: len(all_questions_for_role(role)) for role in QUESTION_BANK
    }
    return status


@app.post("/questions/daily/generate")
async def daily_questions_generate(force: bool = False):
    from services.daily_question_generator import generate_daily_questions

    try:
        return generate_daily_questions(force=force)
    except Exception as exc:
        raise HTTPException(500, f"Daily LLM generation failed: {exc}") from exc


@app.post("/questions/daily/run")
async def daily_questions_run(force: bool = False):
    from services.daily_question_pipeline import run_daily_question_pipeline

    try:
        return run_daily_question_pipeline(force=force)
    except Exception as exc:
        raise HTTPException(500, f"Daily pipeline failed: {exc}") from exc


@app.get("/questions/{role}")
async def list_questions(role: Role):
    from rubrics.sample_rubrics import SAMPLE_RUBRICS
    from workflows.interview_agents.question_bank import all_questions_for_role

    questions = [
        {"question_id": r.question_id, "question": r.question}
        for r in SAMPLE_RUBRICS
        if r.role == role
    ]
    bank = all_questions_for_role(role.value)
    return {
        "role": role.value,
        "questions": questions,
        "total_in_bank": len(bank),
    }


@app.get("/me/evaluations", response_model=list[EvaluationHistoryItem])
async def my_evaluations(
    limit: int = 20,
    user: User = Depends(get_current_user),
):
    db = get_db()
    if db is None:
        raise HTTPException(503, "Database not available")
    try:
        records = EvaluationRepository(db).list_recent(limit=limit, user_id=user.id)
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
    client_metrics: str | None = Form(None),
    user_id=Depends(get_current_user_id_optional),
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
            user_id=user_id,
            client_metrics_raw=client_metrics,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Evaluation failed: {e}") from e


@app.get(
    "/interview/questions/{role}/random",
    response_model=InterviewPreviewQuestionResponse,
)
async def random_interview_question(role: Role, difficulty: int = 3):
    """Random question from the LangGraph role bank (for Up next preview / shuffle)."""
    if interview_service is None:
        raise HTTPException(503, "Service not ready")
    try:
        data = interview_service.random_preview(role=role.value, difficulty=difficulty)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return InterviewPreviewQuestionResponse(
        role=role,
        question_id=data["question_id"],
        question=data["question"],
        competency=data["competency"],
        difficulty=data["difficulty"],
        source=data["source"],
    )


@app.post("/interview/sessions", response_model=InterviewSessionResponse)
async def create_interview_session(body: InterviewSessionCreate):
    if interview_service is None:
        raise HTTPException(503, "Service not ready")
    data = interview_service.create_session(
        role=body.role.value,
        max_turns=body.max_turns,
        difficulty=body.difficulty,
        first_question_id=body.first_question_id,
    )
    return InterviewSessionResponse(
        session_id=data["session_id"],
        role=body.role,
        max_turns=data["max_turns"],
        difficulty=data["difficulty"],
    )


@app.post("/interview/sessions/{session_id}/start", response_model=InterviewQuestionResponse)
async def start_interview_session(session_id: str):
    if interview_service is None:
        raise HTTPException(503, "Service not ready")
    try:
        data = await interview_service.start(session_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return InterviewQuestionResponse(**data)


@app.post("/interview/sessions/{session_id}/turn", response_model=InterviewTurnResponse)
async def interview_turn(session_id: str, body: InterviewTurnRequest):
    if interview_service is None:
        raise HTTPException(503, "Service not ready")
    try:
        data = await interview_service.submit_answer(session_id, body.answer)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return InterviewTurnResponse(**data)


@app.post(
    "/interview/sessions/{session_id}/turn/video",
    response_model=InterviewVideoTurnResponse,
)
async def interview_video_turn(
    session_id: str,
    gpu_consent: str | None = Form(None),
    video: UploadFile = File(...),
    client_metrics: str | None = Form(None),
    user_id=Depends(get_current_user_id_optional),
):
    if interview_service is None or orchestrator is None:
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
        data = await interview_service.submit_video_turn(
            session_id=session_id,
            video_bytes=content,
            filename=video.filename,
            orchestrator=orchestrator,
            gpu_consent=consent,
            user_id=user_id,
            client_metrics_raw=client_metrics,
        )
        return InterviewVideoTurnResponse(**data)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Video turn failed: {e}") from e


@app.get("/interview/sessions/{session_id}")
async def get_interview_session(session_id: str):
    if interview_service is None:
        raise HTTPException(503, "Service not ready")
    data = interview_service.get_session(session_id)
    if not data:
        raise HTTPException(404, "Session not found")
    return data


@app.websocket("/ws/interview/{session_id}")
async def interview_live_stream(websocket: WebSocket, session_id: str):
    """
    WebRTC-adjacent live interview channel (Friday-style).
    Protocol: start | answer | ping  →  question | turn_result | error
    """
    await websocket.accept()
    if interview_service is None:
        await websocket.send_json({"type": "error", "message": "Service not ready"})
        await websocket.close()
        return

    if interview_service.get_session(session_id) is None:
        from workflows.interview_agents import session_store

        if session_store.get(session_id) is None:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            await websocket.close()
            return

    try:
        await websocket.send_json({"type": "connected", "session_id": session_id})

        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "start":
                data = await interview_service.start(session_id)
                await websocket.send_json({"type": "question", **data})
                continue

            if msg_type == "answer":
                answer = (raw.get("answer") or "").strip()
                if not answer:
                    await websocket.send_json({"type": "error", "message": "Empty answer"})
                    continue
                data = await interview_service.submit_answer(session_id, answer)
                await websocket.send_json({"type": "turn_result", **data})
                if data.get("session_complete"):
                    summary = interview_service.get_session(session_id)
                    await websocket.send_json({"type": "session_complete", "summary": summary})
                elif data.get("next_question"):
                    await websocket.send_json(
                        {
                            "type": "question",
                            "session_id": session_id,
                            "question": data["next_question"],
                            "question_id": data.get("next_question_id"),
                            "competency": data.get("competency"),
                            "difficulty": data.get("difficulty"),
                            "turn_number": data.get("turn_number"),
                            "agent_trace": data.get("agent_trace", []),
                        }
                    )
                continue

            await websocket.send_json(
                {"type": "error", "message": f"Unknown message type: {msg_type}"}
            )
    except WebSocketDisconnect:
        pass
    except ValueError as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"Interview stream failed: {e}"})


@app.websocket("/ws/evaluation-progress")
async def evaluation_progress(websocket: WebSocket):
    """Optional real-time progress channel for video evaluation."""
    await websocket.accept()
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Submit video via POST /evaluate for multimodal scoring.",
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
