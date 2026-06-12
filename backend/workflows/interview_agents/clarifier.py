from __future__ import annotations

from workflows.interview_agents.state import InterviewState


async def clarifier_node(state: InterviewState) -> dict:
    grading = state.get("grading", {})
    competency = grading.get("competency", state.get("current_competency", "general"))
    gaps = grading.get("gaps", [])

    gap_hint = gaps[0] if gaps else f"foundational understanding of {competency.replace('_', ' ')}"
    probe = (
        f"Let's step back — can you explain the basics of {competency.replace('_', ' ')} "
        f"and give one concrete example? I noticed: {gap_hint}."
    )

    return {
        "follow_up_needed": True,
        "follow_up_question": probe,
        "clarifier_active": True,
    }
