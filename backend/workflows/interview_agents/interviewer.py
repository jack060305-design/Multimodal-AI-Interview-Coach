from __future__ import annotations

from workflows.interview_agents.question_bank import (
    pick_competency,
    search_question_bank,
    session_rng,
)
from workflows.interview_agents.state import InterviewState


async def interviewer_node(state: InterviewState) -> dict:
    if state.get("follow_up_needed") and state.get("follow_up_question"):
        return {
            "current_question": state["follow_up_question"],
            "current_question_id": state.get("current_question_id", ""),
            "follow_up_needed": False,
            "follow_up_question": "",
            "coach_directives": [],
        }

    competency = pick_competency(state)
    rng = session_rng(state)
    picked = search_question_bank(
        role=state["role"],
        competency=competency,
        difficulty=state.get("difficulty", 3),
        exclude_ids=state.get("asked_question_ids", []),
        rng=rng,
    )

    if not picked:
        picked_comp = competency
        question = (
            f"Tell me about a time you demonstrated {picked_comp.replace('_', ' ')} "
            f"in a {state['role'].replace('_', ' ')} context."
        )
        qid = f"generated_{state.get('turn_number', 0)}"
    else:
        question = picked.question
        qid = picked.question_id
        competency = picked.competency

    asked = list(state.get("asked_question_ids", []))
    if qid and qid not in asked:
        asked.append(qid)

    return {
        "current_question": question,
        "current_question_id": qid,
        "current_competency": competency,
        "asked_question_ids": asked,
        "follow_up_needed": False,
        "follow_up_question": "",
        "coach_directives": [],
        "clarifier_active": False,
    }
