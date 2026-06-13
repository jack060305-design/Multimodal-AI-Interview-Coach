"""Finalize node — mark approved drafts as final output."""

from __future__ import annotations

from workflows.daily_question_agents.llm_utils import append_trace
from workflows.daily_question_agents.state import DailyQuestionState


def finalize_node(state: DailyQuestionState) -> DailyQuestionState:
    state = dict(state)
    approved = state.get("approved_questions") or state.get("draft_questions") or []
    state["approved_questions"] = approved
    append_trace(
        state,
        "finalize",
        f"final={len(approved)}; total_llm_calls={state.get('llm_calls', 0)}",
    )
    return state
