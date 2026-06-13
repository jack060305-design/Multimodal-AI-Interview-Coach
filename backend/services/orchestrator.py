import logging
import shutil
import tempfile
from pathlib import Path

from config import get_settings
from db.database import get_db
from db.repository import EvaluationRepository
from schemas import EvaluationResult, Role
from storage import get_object_store
from utils.gpu_consent import gpu_consent_scope
from workflows import EvaluationGraph

logger = logging.getLogger(__name__)


class EvaluationOrchestrator:
    def __init__(self):
        self.graph = EvaluationGraph()
        self.object_store = get_object_store()
        self.settings = get_settings()

    def evaluate(
        self,
        video_path: str | Path,
        role: Role,
        question: str,
        question_id: str | None = None,
        video_bytes: bytes | None = None,
        filename: str = "recording.webm",
        gpu_consent: str | None = None,
        user_id=None,
        competency: str | None = None,
        client_metrics_raw: str | None = None,
    ) -> EvaluationResult:
        storage_key = None
        if video_bytes and not self.settings.skip_video_storage:
            try:
                storage_key = self.object_store.upload(video_bytes, filename)
            except Exception as exc:
                logger.warning("Video upload skipped: %s", exc)

        with gpu_consent_scope(gpu_consent):
            result = self.graph.run(
                video_path=str(video_path),
                role=role,
                question=question,
                question_id=question_id,
                competency=competency,
                client_metrics_raw=client_metrics_raw,
            )
        result.video_storage_key = storage_key

        self._persist(result, storage_key, user_id=user_id)
        return result

    def evaluate_upload(
        self,
        file_bytes: bytes,
        filename: str,
        role: Role,
        question: str,
        question_id: str | None = None,
        gpu_consent: str | None = None,
        user_id=None,
        competency: str | None = None,
        client_metrics_raw: str | None = None,
    ) -> EvaluationResult:
        suffix = Path(filename).suffix or ".webm"
        tmp_dir = Path(tempfile.mkdtemp(prefix="interview_"))
        try:
            video_path = tmp_dir / f"upload{suffix}"
            video_path.write_bytes(file_bytes)
            return self.evaluate(
                video_path=video_path,
                role=role,
                question=question,
                question_id=question_id,
                video_bytes=file_bytes,
                filename=filename,
                gpu_consent=gpu_consent,
                user_id=user_id,
                competency=competency,
                client_metrics_raw=client_metrics_raw,
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _persist(self, result: EvaluationResult, storage_key: str | None, user_id=None) -> None:
        db = get_db()
        if db is None:
            return
        try:
            EvaluationRepository(db).save(
                result=result,
                video_key=storage_key,
                llm_provider=self.settings.llm_provider,
                vector_store=self.settings.resolved_vector_store,
                user_id=user_id,
            )
        except Exception as exc:
            logger.warning("Failed to persist evaluation: %s", exc)
            db.rollback()
        finally:
            db.close()
