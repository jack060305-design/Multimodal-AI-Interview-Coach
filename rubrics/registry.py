"""In-memory rubric lookup (fallback when Chroma has not been re-ingested)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from schemas import RubricDocument


def rubric_doc_to_payload(doc: RubricDocument) -> dict:
    return {
        "role": doc.role.value,
        "question": doc.question,
        "question_id": doc.question_id,
        "rubric": [c.model_dump() for c in doc.rubric],
        "ideal_answer": doc.ideal_answer,
        "evaluation_guidelines": doc.evaluation_guidelines,
        "total_points": doc.total_points,
    }


def build_rubric_index(rubrics: list[RubricDocument]) -> dict[str, RubricDocument]:
    return {f"{r.role.value}:{r.question_id}": r for r in rubrics}
