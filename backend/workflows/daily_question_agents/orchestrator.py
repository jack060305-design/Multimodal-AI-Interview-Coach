"""Orchestrator for daily question multi-agent LangGraph workflow."""

from __future__ import annotations

import logging
from datetime import date

from config import get_settings
from workflows.daily_question_agents.graph import DailyQuestionAgentGraph
from workflows.daily_question_agents.state import DailyQuestionState

logger = logging.getLogger(__name__)


def run_agentic_daily_generation(*, force: bool = False) -> DailyQuestionState:
    settings = get_settings()
    initial: DailyQuestionState = {
        "day": date.today().isoformat(),
        "per_role": settings.daily_questions_per_role,
        "force": force,
        "revision_round": 0,
        "max_revisions": settings.daily_questions_max_revisions,
        "llm_calls": 0,
        "agent_trace": [],
        "errors": [],
        "draft_questions": [],
        "approved_questions": [],
        "rejected_questions": [],
    }
    logger.info(
        "Starting agentic daily question graph (per_role=%s, max_revisions=%s)",
        initial["per_role"],
        initial["max_revisions"],
    )
    result = DailyQuestionAgentGraph.invoke(initial)
    return result
