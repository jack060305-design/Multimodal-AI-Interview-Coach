"""Refresh in-memory rubrics when daily/cache files change (zero cost)."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LLM_CACHE = _PROJECT_ROOT / "backend" / "data" / "llm_daily_questions.json"
_FEED_CACHE = _PROJECT_ROOT / "backend" / "data" / "question_feed_cache.json"
_last_mtime: float = 0.0


def reload_rubrics_if_stale() -> bool:
    global _last_mtime
    mtimes = [p.stat().st_mtime for p in (_LLM_CACHE, _FEED_CACHE) if p.exists()]
    current = max(mtimes) if mtimes else 0.0
    if current <= _last_mtime:
        return False
    try:
        from rubrics import sample_rubrics
        from workflows.interview_agents import question_bank

        count = sample_rubrics.reload_rubrics()
        question_bank.reload_bank()
        _last_mtime = current
        logger.info("Rubrics refreshed (%s docs)", count)
        return True
    except Exception as exc:
        logger.warning("Rubric refresh failed: %s", exc)
        return False
