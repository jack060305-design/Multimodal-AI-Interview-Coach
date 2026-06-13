"""Load LLM daily-generated questions from backend/data/llm_daily_questions.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from rubrics.star_template import make_behavioral_rubric
from schemas import Role

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LLM_DAILY_CACHE = PROJECT_ROOT / "backend" / "data" / "llm_daily_questions.json"


def load_llm_daily_cache() -> dict:
    if not LLM_DAILY_CACHE.exists():
        return {"generated_at": None, "questions": []}
    try:
        return json.loads(LLM_DAILY_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"generated_at": None, "questions": []}


def load_llm_daily_rubrics() -> list:
    rubrics = []
    for entry in load_llm_daily_cache().get("questions", []):
        role = Role(entry["role"])
        rubrics.append(
            make_behavioral_rubric(
                role=role,
                question_id=entry["question_id"],
                question=entry["question"],
                ideal_answer_hint=entry.get("ideal_answer_hint"),
            )
        )
    return rubrics


def llm_daily_question_meta() -> dict[str, tuple[str, int]]:
    meta: dict[str, tuple[str, int]] = {}
    for entry in load_llm_daily_cache().get("questions", []):
        meta[entry["question_id"]] = (
            entry.get("competency", "communication"),
            int(entry.get("difficulty", 3)),
        )
    return meta


def llm_daily_question_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for entry in load_llm_daily_cache().get("questions", []):
        qid = entry.get("question_id")
        if qid:
            sources[qid] = entry.get("source", "llm_daily")
    return sources
