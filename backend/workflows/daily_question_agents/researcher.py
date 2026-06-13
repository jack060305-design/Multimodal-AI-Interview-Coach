"""Researcher agent — no LLM; builds brief from cached feeds and existing bank."""

from __future__ import annotations

import json
from pathlib import Path

from schemas import Role
from workflows.daily_question_agents.llm_utils import append_trace
from workflows.daily_question_agents.state import DailyQuestionState

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FEED_CACHE = PROJECT_ROOT / "backend" / "data" / "question_feed_cache.json"
LLM_CACHE = PROJECT_ROOT / "backend" / "data" / "llm_daily_questions.json"


def _load_feed_samples(limit: int = 15) -> list[str]:
    if not FEED_CACHE.exists():
        return []
    try:
        data = json.loads(FEED_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [q.get("question", "") for q in data.get("questions", [])[:limit] if q.get("question")]


def _load_recent_llm(limit: int = 12) -> list[str]:
    if not LLM_CACHE.exists():
        return []
    try:
        data = json.loads(LLM_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [q.get("question", "") for q in data.get("questions", [])[-limit:] if q.get("question")]


def _bank_snippets(limit: int = 20) -> list[str]:
    from rubrics.sample_rubrics import SAMPLE_RUBRICS

    return [doc.question for doc in SAMPLE_RUBRICS[:limit]]


def _role_feed_samples(role: str, limit: int = 5) -> list[str]:
    if not FEED_CACHE.exists():
        return []
    try:
        data = json.loads(FEED_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    matched = [
        q.get("question", "")
        for q in data.get("questions", [])
        if role in (q.get("roles") or []) or q.get("role") == role
    ]
    return [m for m in matched if m][:limit]


def researcher_node(state: DailyQuestionState) -> DailyQuestionState:
    """Compile research brief from local caches — zero LLM cost."""
    state = dict(state)
    plan = state.get("plan") or {}
    theme = state.get("theme") or plan.get("theme", "")

    feed_samples = _load_feed_samples()
    recent_llm = _load_recent_llm()
    bank = _bank_snippets()
    avoid = list(dict.fromkeys(recent_llm + bank[:15]))

    sections = [
        f"Theme: {theme}",
        f"Planner rationale: {plan.get('rationale', '')}",
        "",
        "External feed samples (trends from GitHub behavioral repo):",
    ]
    sections.extend(f"- {q}" for q in feed_samples[:10] or ["(no feed cache yet)"])

    sections.append("")
    sections.append("Per-role external matches:")
    for role in Role:
        samples = _role_feed_samples(role.value)
        if samples:
            sections.append(f"  {role.value}:")
            sections.extend(f"    - {q}" for q in samples)

    sections.append("")
    sections.append("Recently generated / bank questions to AVOID duplicating:")
    sections.extend(f"- {q}" for q in avoid[:20])

    state["research_brief"] = "\n".join(sections)
    state["avoid_questions"] = avoid
    append_trace(
        state,
        "researcher",
        f"brief={len(state['research_brief'])} chars; avoid={len(avoid)}; llm_calls=0",
    )
    return state
