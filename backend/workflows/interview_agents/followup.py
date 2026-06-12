from __future__ import annotations

from workflows.interview_agents.session_memory import find_recurring_gaps
from workflows.interview_agents.state import InterviewState


async def followup_node(state: InterviewState) -> dict:
    grading = state.get("grading", {})
    score = int(grading.get("score", 3))
    gaps = grading.get("gaps", [])
    suggestion = grading.get("follow_up_suggestion", "")
    competency = grading.get("competency", state.get("current_competency", "general"))

    recurring = find_recurring_gaps(
        state.get("turn_embeddings", []),
        competency,
        min_score=3,
    )

    should_followup = score <= 3 and (bool(gaps) or recurring or bool(suggestion))

    if not should_followup:
        return {"follow_up_needed": False, "follow_up_question": ""}

    if suggestion:
        return {"follow_up_needed": True, "follow_up_question": suggestion}

    gap_text = gaps[0] if gaps else f"recurring weakness in {competency.replace('_', ' ')}"
    question = (
        f"Following up on your last answer — can you elaborate on {gap_text} "
        f"with a specific situation and outcome?"
    )
    return {"follow_up_needed": True, "follow_up_question": question}
