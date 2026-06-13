"""Conditional routing after critic evaluation."""

from __future__ import annotations

from workflows.daily_question_agents.state import DailyQuestionState


def route_after_critic(state: DailyQuestionState) -> str:
    rejected = state.get("rejected_questions") or []
    revision_round = int(state.get("revision_round", 0))
    max_revisions = int(state.get("max_revisions", 1))

    if rejected and revision_round < max_revisions:
        return "generator"
    return "finalize"
