from __future__ import annotations

from workflows.interview_agents.state import InterviewState


def route_after_grader(state: InterviewState) -> str:
    score = state.get("grading", {}).get("score", 3)
    if score <= 2:
        return "clarifier"
    if score == 5:
        return "coach"
    return "followup"


def route_after_followup(state: InterviewState) -> str:
    if state.get("follow_up_needed"):
        return "interviewer"
    return "coach"
