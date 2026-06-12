from __future__ import annotations

from workflows.interview_agents.state import InterviewState


async def coach_node(state: InterviewState) -> dict:
    scores = state.get("competency_scores", {})
    difficulty = state.get("difficulty", 3)
    budget = dict(state.get("question_budget", {}))
    banned = list(state.get("banned_competencies", []))
    directives: list[str] = []
    notes: list[str] = []

    if scores:
        rolling = sum(scores.values()) / len(scores)
        if rolling >= 4.0 and difficulty < 5:
            difficulty += 1
            directives.append("Increase difficulty — candidate is performing strongly.")
        elif rolling <= 2.0 and difficulty > 1:
            difficulty -= 1
            directives.append("Lower difficulty — reinforce fundamentals.")

    competency = state.get("grading", {}).get("competency", state.get("current_competency"))
    if competency and competency in budget:
        budget[competency] = max(0, budget[competency] - 1)
        if budget[competency] == 0 and competency not in banned:
            banned.append(competency)
            directives.append(f"Move on from '{competency}' — question budget exhausted.")

    exhausted = all(v <= 0 for v in budget.values()) if budget else False
    turn = state.get("turn_number", 0)
    max_turns = state.get("max_turns", 5)
    session_complete = exhausted or turn >= max_turns

    grading = state.get("grading", {})
    if grading.get("feedback"):
        notes.append(str(grading["feedback"]))

    return {
        "difficulty": difficulty,
        "question_budget": budget,
        "banned_competencies": banned,
        "coach_directives": directives,
        "coaching_notes": state.get("coaching_notes", []) + notes,
        "session_complete": session_complete,
    }
