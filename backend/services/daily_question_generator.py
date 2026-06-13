"""Daily interview question generation — simple LLM or LangGraph multi-agent."""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import get_settings
from rubric_engine.local_evaluator import _has_valid_llm_key
from rubrics.external_feed_loader import infer_competency
from rubrics.llm_daily_loader import LLM_DAILY_CACHE, load_llm_daily_cache
from schemas import Role

logger = logging.getLogger(__name__)

LLM_RETENTION_DAYS = 7

ROLE_LABELS = {
    Role.SWE_INTERN: "Software Engineering Intern",
    Role.DATA_ANALYST: "Data Analyst",
    Role.FINANCE_ANALYST: "Finance Analyst",
    Role.PRODUCT_MANAGER: "Product Manager",
}

WEEKLY_THEMES = [
    "teamwork and conflict resolution",
    "handling pressure and tight deadlines",
    "learning from failure and adaptability",
    "communication with non-technical stakeholders",
    "prioritization and trade-offs",
    "leadership and initiative",
    "recent industry trends and AI in the workplace",
]

GENERATOR_SYSTEM = """You create high-quality mock interview questions for job candidates.
Output ONLY valid JSON. Questions must be realistic, specific, and answerable in 2-3 minutes.
Avoid duplicates of common textbook prompts when possible — add a fresh angle tied to the theme."""

GENERATOR_USER = """Role: {role_label}
Theme for today: {theme}
Date: {today}

Generate exactly {count} NEW behavioral or role-relevant interview questions.
Each question should fit the role and theme. Prefer STAR-style behavioral prompts.

Existing questions to AVOID repeating (sample):
{avoid_sample}

Return JSON:
{{
  "questions": [
    {{
      "question": "...",
      "competency": "communication|problem_solving|execution|collaboration|adaptability",
      "difficulty": 1-5,
      "ideal_answer_hint": "brief STAR outline for a strong answer"
    }}
  ]
}}"""


def _existing_question_snippets(limit: int = 25) -> str:
    from rubrics.sample_rubrics import SAMPLE_RUBRICS

    lines = [f"- {doc.question}" for doc in SAMPLE_RUBRICS[:limit]]
    return "\n".join(lines) or "(none)"


def _question_id(role: str, question: str, day: str) -> str:
    digest = hashlib.sha1(f"{day}:{role}:{question}".encode()).hexdigest()[:10]
    return f"llm_{day.replace('-', '')}_{role[:3]}_{digest}"


def _theme_for_today() -> str:
    return WEEKLY_THEMES[date.today().toordinal() % len(WEEKLY_THEMES)]


def llm_daily_status() -> dict:
    cache = load_llm_daily_cache()
    counts: dict[str, int] = {}
    for entry in cache.get("questions", []):
        role = entry.get("role", "unknown")
        counts[role] = counts.get(role, 0) + 1
    settings = get_settings()
    return {
        "generated_at": cache.get("generated_at"),
        "total": len(cache.get("questions", [])),
        "by_role": counts,
        "theme_today": cache.get("theme") or _theme_for_today(),
        "mode": cache.get("mode") or settings.daily_questions_mode,
        "llm_calls_last_run": cache.get("llm_calls"),
        "agent_trace": cache.get("agent_trace"),
        "critic_notes": cache.get("critic_notes"),
        "cache_path": str(LLM_DAILY_CACHE),
    }


def _call_llm_json(system: str, user: str) -> dict:
    from rubric_engine.evaluator import RubricEvaluator

    raw = RubricEvaluator()._call_llm(system, user)
    return json.loads(raw)


def _generate_for_role_simple(role: Role, count: int, theme: str, day: str) -> list[dict]:
    user = GENERATOR_USER.format(
        role_label=ROLE_LABELS[role],
        theme=theme,
        today=day,
        count=count,
        avoid_sample=_existing_question_snippets(),
    )
    data = _call_llm_json(GENERATOR_SYSTEM, user)
    entries: list[dict] = []
    seen_text: set[str] = set()

    for item in data.get("questions", [])[:count]:
        question = str(item.get("question", "")).strip()
        if len(question) < 15 or question.lower() in seen_text:
            continue
        seen_text.add(question.lower())
        qid = _question_id(role.value, question, day)
        competency = str(item.get("competency") or infer_competency(question))
        if competency not in (
            "communication",
            "problem_solving",
            "execution",
            "collaboration",
            "adaptability",
        ):
            competency = infer_competency(question)

        entries.append(
            {
                "question_id": qid,
                "question": question if question.endswith("?") else f"{question}?",
                "role": role.value,
                "competency": competency,
                "difficulty": max(1, min(5, int(item.get("difficulty", 3)))),
                "ideal_answer_hint": str(item.get("ideal_answer_hint", "")).strip(),
                "source": "llm_daily",
                "generated_on": day,
                "theme": theme,
            }
        )
    return entries


def _prune_old(entries: list[dict]) -> list[dict]:
    cutoff = date.today().toordinal() - LLM_RETENTION_DAYS
    kept = []
    for entry in entries:
        try:
            d = date.fromisoformat(entry.get("generated_on", ""))
            if d.toordinal() >= cutoff:
                kept.append(entry)
        except ValueError:
            kept.append(entry)
    return kept


def _persist_questions(
    new_entries: list[dict],
    *,
    theme: str,
    mode: str,
    agent_trace: list | None = None,
    llm_calls: int | None = None,
    critic_notes: str | None = None,
    errors: list[str] | None = None,
) -> dict:
    cache = load_llm_daily_cache()
    merged = _prune_old(cache.get("questions", []))
    existing_ids = {e["question_id"] for e in merged}
    for entry in new_entries:
        if entry["question_id"] not in existing_ids:
            merged.append(entry)
            existing_ids.add(entry["question_id"])

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "theme": theme,
        "mode": mode,
        "llm_calls": llm_calls,
        "agent_trace": agent_trace,
        "critic_notes": critic_notes,
        "questions": merged,
    }
    LLM_DAILY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    LLM_DAILY_CACHE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    from rubrics import sample_rubrics
    from workflows.interview_agents import question_bank

    sample_rubrics.reload_rubrics()
    counts = question_bank.reload_bank()

    return {
        "ok": True,
        "skipped": False,
        "generated": len(new_entries),
        "theme": theme,
        "mode": mode,
        "llm_calls": llm_calls,
        "agent_trace": agent_trace,
        "critic_notes": critic_notes,
        "errors": errors or None,
        "counts_by_role": counts,
        **llm_daily_status(),
    }


def _generate_agentic(*, force: bool, today: str) -> dict:
    from workflows.daily_question_agents.orchestrator import run_agentic_daily_generation

    graph_result = run_agentic_daily_generation(force=force)
    new_entries = graph_result.get("approved_questions") or []
    errors = list(graph_result.get("errors") or [])

    if not new_entries and errors:
        return {"ok": False, "errors": errors, "mode": "agentic", **llm_daily_status()}

    return _persist_questions(
        new_entries,
        theme=graph_result.get("theme") or _theme_for_today(),
        mode="agentic",
        agent_trace=graph_result.get("agent_trace"),
        llm_calls=graph_result.get("llm_calls"),
        critic_notes=graph_result.get("critic_notes"),
        errors=errors or None,
    )


def _generate_simple(*, today: str, per_role: int) -> dict:
    theme = _theme_for_today()
    new_entries: list[dict] = []
    errors: list[str] = []

    for role in Role:
        try:
            new_entries.extend(_generate_for_role_simple(role, per_role, theme, today))
        except Exception as exc:
            logger.exception("LLM daily generation failed for %s", role.value)
            errors.append(f"{role.value}: {exc}")

    if not new_entries and errors:
        return {"ok": False, "errors": errors, "mode": "simple"}

    return _persist_questions(
        new_entries,
        theme=theme,
        mode="simple",
        llm_calls=len(Role),
        errors=errors or None,
    )


def generate_daily_questions(*, force: bool = False) -> dict:
    """Generate fresh questions for all roles (agentic LangGraph or simple LLM)."""
    settings = get_settings()
    if not settings.daily_questions_enabled and not force:
        return {"ok": False, "skipped": True, "reason": "DAILY_QUESTIONS_ENABLED=false"}

    if not _has_valid_llm_key():
        return {"ok": False, "skipped": True, "reason": "no LLM API key configured"}

    today = date.today().isoformat()
    cache = load_llm_daily_cache()
    existing_today = [
        q for q in cache.get("questions", []) if q.get("generated_on") == today
    ]
    if existing_today and not force:
        return {
            "ok": True,
            "skipped": True,
            "reason": f"already generated today ({len(existing_today)} questions)",
            **llm_daily_status(),
        }

    mode = settings.daily_questions_mode.lower()
    if mode == "agentic":
        return _generate_agentic(force=force, today=today)
    return _generate_simple(today=today, per_role=settings.daily_questions_per_role)
