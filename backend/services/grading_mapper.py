from __future__ import annotations

from schemas import EvaluationResult


def grading_from_evaluation(evaluation: EvaluationResult, competency: str) -> dict:
    """Map full multimodal evaluation to interview turn grading (no extra LLM call)."""
    score_1_5 = max(1, min(5, int(round(evaluation.overall_score / 20))))
    gaps: list[str] = []
    if score_1_5 <= 2:
        gaps.append("Answer needs more depth against the rubric")
    if evaluation.metrics.filler_words.rate > 6:
        gaps.append(f"High filler rate ({evaluation.metrics.filler_words.rate}%)")
    if evaluation.metrics.eye_contact.percentage < 60:
        gaps.append(f"Low eye contact ({evaluation.metrics.eye_contact.percentage}%)")
    gaps.extend(evaluation.improvement_suggestions[:2])

    feedback = (
        evaluation.metrics.technical_depth.comment
        or evaluation.metrics.response_quality.comment
        or "See rubric breakdown in evaluation."
    )
    return {
        "score": score_1_5,
        "competency": competency,
        "feedback": feedback,
        "strengths": ["Clear multimodal evaluation completed"] if score_1_5 >= 3 else [],
        "gaps": gaps[:4],
        "follow_up_suggestion": evaluation.improvement_suggestions[0]
        if evaluation.improvement_suggestions
        else "",
    }
