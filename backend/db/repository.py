from uuid import UUID

from sqlalchemy.orm import Session

from db.models import EvaluationRecord
from schemas import EvaluationResult, PerformanceSummary


class EvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(
        self,
        result: EvaluationResult,
        video_key: str | None,
        llm_provider: str,
        vector_store: str,
        user_id: UUID | None = None,
    ) -> EvaluationRecord:
        record = EvaluationRecord(
            id=result.evaluation_id,
            user_id=user_id,
            role=result.role.value,
            question_id=result.question_id,
            question=result.question,
            video_storage_key=video_key,
            transcript=result.transcript,
            overall_score=result.overall_score,
            delivery_score=result.performance.delivery.score,
            communication_score=result.performance.communication.score,
            technical_score=result.performance.technical_depth.score,
            result_json=result.model_dump(mode="json"),
            llm_provider=llm_provider,
            vector_store=vector_store,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_recent(self, limit: int = 20, user_id: UUID | None = None) -> list[EvaluationRecord]:
        q = self.db.query(EvaluationRecord)
        if user_id is not None:
            q = q.filter(EvaluationRecord.user_id == user_id)
        return q.order_by(EvaluationRecord.created_at.desc()).limit(limit).all()

    def get(self, evaluation_id: UUID) -> EvaluationRecord | None:
        return (
            self.db.query(EvaluationRecord)
            .filter(EvaluationRecord.id == evaluation_id)
            .first()
        )
