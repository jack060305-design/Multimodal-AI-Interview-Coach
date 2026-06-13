"""STAR-style rubric factory for behavioral / job-search interview questions."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from schemas import Role, RubricCriterion, RubricDocument


def _levels(zero: str, five: str, eight: str, ten: str) -> dict[str, str]:
    return {"0": zero, "5": five, "8": eight, "10": ten}


def _criterion(name: str, weight: int, levels: dict[str, str]) -> RubricCriterion:
    return RubricCriterion(criterion=name, weight=weight, levels=levels)


def make_behavioral_rubric(
    *,
    role: Role,
    question_id: str,
    question: str,
    competency: str = "communication",
    ideal_answer_hint: str | None = None,
) -> RubricDocument:
    hint = ideal_answer_hint or (
        "Use STAR (Situation, Task, Action, Result). Be specific, quantify impact, "
        "and reflect on what you learned."
    )
    return RubricDocument(
        role=role,
        question_id=question_id,
        question=question.strip(),
        ideal_answer=hint,
        evaluation_guidelines=(
            "Score using STAR structure, relevance to the question, and professional tone. "
            "Full credit requires a concrete past example with measurable or clear outcome."
        ),
        rubric=[
            _criterion(
                "STAR structure",
                30,
                _levels(
                    "No structure or off-topic",
                    "Partial STAR with vague details",
                    "Clear STAR with one concrete example",
                    "Crisp STAR with metrics and reflection",
                ),
            ),
            _criterion(
                "Relevance and depth",
                35,
                _levels(
                    "Does not answer the question",
                    "Surface-level answer",
                    "Direct answer with reasonable depth",
                    "Insightful answer tailored to role and company context",
                ),
            ),
            _criterion(
                "Communication and professionalism",
                35,
                _levels(
                    "Negative, rambling, or unprofessional",
                    "Understandable but unfocused",
                    "Clear and professional",
                    "Concise, confident, and authentic",
                ),
            ),
        ],
    )
