"""Shared state for daily question multi-agent LangGraph workflow."""

from typing import Any, TypedDict


class DailyQuestionState(TypedDict, total=False):
    day: str
    per_role: int
    theme: str
    force: bool

    plan: dict[str, Any]
    research_brief: str
    avoid_questions: list[str]

    draft_questions: list[dict[str, Any]]
    approved_questions: list[dict[str, Any]]
    rejected_questions: list[dict[str, Any]]
    critic_notes: str

    revision_round: int
    max_revisions: int
    llm_calls: int

    agent_trace: list[dict[str, str]]
    errors: list[str]
