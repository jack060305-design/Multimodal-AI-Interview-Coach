from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Role(str, Enum):
    SWE_INTERN = "swe_intern"
    DATA_ANALYST = "data_analyst"
    FINANCE_ANALYST = "finance_analyst"
    PRODUCT_MANAGER = "product_manager"


class RubricLevel(BaseModel):
    score: int
    description: str


class RubricCriterion(BaseModel):
    criterion: str
    weight: int = Field(ge=0, le=100)
    levels: dict[str, str]


class RubricDocument(BaseModel):
    role: Role
    question: str
    question_id: str
    rubric: list[RubricCriterion]
    ideal_answer: str
    total_points: int = 100
    evaluation_guidelines: str = ""


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    words: list[dict[str, Any]] = []


class TranscriptResult(BaseModel):
    text: str
    segments: list[TranscriptSegment]
    language: str = "en"
    duration_seconds: float = 0.0


class EyeContactMetric(BaseModel):
    score: int
    percentage: float
    comment: str
    head_movement_score: int | None = None
    posture_score: int | None = None


class FillerWordsMetric(BaseModel):
    score: int
    count: int
    rate: float
    top_fillers: list[str]
    wpm: float
    long_pauses: int


class ConfidenceFactors(BaseModel):
    voice: float
    language: float
    eye_contact: float
    filler_penalty: float


class ConfidenceMetric(BaseModel):
    score: int
    factors: ConfidenceFactors


class CriterionScore(BaseModel):
    criterion: str
    score: int
    max_score: int = 10
    evidence: str
    justification: str


class TechnicalDepthMetric(BaseModel):
    score: int
    breakdown: list[CriterionScore]
    comment: str


class ResponseQualityMetric(BaseModel):
    score: int
    breakdown: list[CriterionScore]
    comment: str


class EvaluationMetrics(BaseModel):
    eye_contact: EyeContactMetric
    filler_words: FillerWordsMetric
    confidence: ConfidenceMetric
    technical_depth: TechnicalDepthMetric
    response_quality: ResponseQualityMetric


class PerformanceCategory(BaseModel):
    score: int
    label: str
    summary: str
    signals: list[str] = []


class PerformanceSummary(BaseModel):
    delivery: PerformanceCategory
    communication: PerformanceCategory
    technical_depth: PerformanceCategory


class EvaluationResult(BaseModel):
    evaluation_id: UUID = Field(default_factory=uuid4)
    overall_score: int
    role: Role
    question: str
    question_id: str
    transcript: str
    performance: PerformanceSummary
    metrics: EvaluationMetrics
    improvement_suggestions: list[str]
    video_storage_key: str | None = None


class GpuConsentRequest(BaseModel):
    choice: str = Field(description="always | never | reset")


class EvaluationHistoryItem(BaseModel):
    evaluation_id: UUID
    role: Role
    question_id: str
    question: str
    overall_score: int
    delivery_score: int
    communication_score: int
    technical_score: int
    created_at: str
    video_storage_key: str | None = None
