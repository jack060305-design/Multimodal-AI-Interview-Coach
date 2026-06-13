"""Daily scheduled pipeline: external feed sync + LLM question generation."""

from __future__ import annotations

import logging

from services.daily_question_generator import generate_daily_questions
from services.question_feed_sync import sync_question_feed

logger = logging.getLogger(__name__)


def run_daily_question_pipeline(*, force: bool = False) -> dict:
    """Run full daily update (GitHub feed + LLM). Called by scheduler or manual trigger."""
    logger.info("Starting daily question pipeline (force=%s)", force)

    feed_result = sync_question_feed(force=force)
    llm_result = generate_daily_questions(force=force)

    return {
        "ok": feed_result.get("ok", False) or llm_result.get("ok", False),
        "feed": feed_result,
        "llm_daily": llm_result,
    }
