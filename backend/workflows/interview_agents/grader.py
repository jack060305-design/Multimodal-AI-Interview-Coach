from __future__ import annotations

import json
import os
import re
from typing import Any

from rubric_engine.store_factory import get_vector_store
from schemas import Role, TranscriptResult
from workflows.interview_agents.state import InterviewState


def _update_competency_scores(current: dict[str, float], competency: str, score: int) -> dict[str, float]:
    updated = dict(current)
    if competency in updated:
        updated[competency] = (updated[competency] + score) / 2
    else:
        updated[competency] = float(score)
    return updated


def _local_grade(answer: str, rubric_payload: dict[str, Any], competency: str) -> dict[str, Any]:
    from rubric_engine.local_evaluator import evaluate_local

    transcript = TranscriptResult(text=answer, segments=[], duration_seconds=60.0)
    result = evaluate_local(Role(rubric_payload["role"]), transcript, rubric_payload)
    tech = result["technical_depth"].score
    resp = result["response_quality"].score
    blended = (tech + resp) / 2
    score_1_5 = max(1, min(5, int(round(blended / 20))))

    gaps = []
    if score_1_5 <= 2:
        gaps.append("Answer lacks depth or key rubric points")
    if len(re.findall(r"\b\w+\b", answer)) < 30:
        gaps.append("Needs more detail and concrete examples")

    return {
        "score": score_1_5,
        "competency": competency,
        "feedback": result["technical_depth"].comment,
        "strengths": ["Addresses the question"] if score_1_5 >= 3 else [],
        "gaps": gaps,
        "follow_up_suggestion": (
            f"Can you go deeper on {competency.replace('_', ' ')} with a specific example?"
            if gaps
            else ""
        ),
    }


def _llm_grade(state: InterviewState, rubric_payload: dict[str, Any], competency: str) -> dict[str, Any] | None:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "local":
        return None

    from rubric_engine.evaluator import RubricEvaluator

    prompt = (
        f"Question: {state['current_question']}\n"
        f"Answer: {state['current_answer']}\n"
        f"Competency: {competency}\n"
        "Return JSON: score (1-5), competency, feedback, strengths[], gaps[], follow_up_suggestion"
    )
    try:
        ev = RubricEvaluator()
        raw = ev._call_llm(
            "You grade interview answers. Return JSON only.",
            f"Rubric:\n{json.dumps(rubric_payload.get('rubric', []))}\n\n{prompt}",
        )
        data = json.loads(raw)
        if "technical_depth" in data:
            tech = data["technical_depth"].get("score", 50)
            score = max(1, min(5, int(round(tech / 20))))
            return {
                "score": score,
                "competency": competency,
                "feedback": data["technical_depth"].get("comment", ""),
                "strengths": [],
                "gaps": [],
                "follow_up_suggestion": "",
            }
        data["score"] = max(1, min(5, int(data.get("score", 3))))
        return data
    except Exception:
        return None


async def grader_node(state: InterviewState) -> dict[str, Any]:
    competency = state.get("current_competency", "general")
    store = get_vector_store()
    role = Role(state["role"])

    payload = None
    qid = state.get("current_question_id")
    if qid:
        payload = store.get_by_question_id(role, qid)
    if not payload:
        retrieved = store.retrieve(role, state["current_question"], k=1)
        payload = retrieved[0] if retrieved else None

    if payload:
        grading = _llm_grade(state, payload, competency) or _local_grade(
            state["current_answer"], payload, competency
        )
    else:
        word_count = len(re.findall(r"\b\w+\b", state["current_answer"]))
        score = 2 if word_count < 15 else 3 if word_count < 40 else 4
        grading = {
            "score": score,
            "competency": competency,
            "feedback": "Graded without rubric match.",
            "strengths": [],
            "gaps": [] if score >= 3 else ["Expand with examples"],
            "follow_up_suggestion": "",
        }

    competency = grading.get("competency", competency)
    score = int(grading.get("score", 3))
    updated = _update_competency_scores(state.get("competency_scores", {}), competency, score)

    return {"grading": grading, "competency_scores": updated}
