"""Load externally synced interview questions from backend/data/question_feed_cache.json."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from schemas import Role
from rubrics.star_template import make_behavioral_rubric

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = PROJECT_ROOT / "backend" / "data" / "question_feed_cache.json"

ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "swe_intern": (
        "technical",
        "code",
        "software",
        "engineer",
        "debug",
        "system",
        "api",
        "program",
    ),
    "data_analyst": ("data", "metric", "analysis", "sql", "a/b", "experiment", "dashboard"),
    "finance_analyst": ("financial", "finance", "model", "forecast", "variance", "budget"),
    "product_manager": (
        "product",
        "roadmap",
        "stakeholder",
        "user",
        "customer",
        "feature",
        "priority",
    ),
}


def _slug(text: str, prefix: str = "feed") -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def infer_roles(question: str) -> list[Role]:
    lower = question.lower()
    matched: list[Role] = []
    for role_key, keywords in ROLE_KEYWORDS.items():
        if any(k in lower for k in keywords):
            matched.append(Role(role_key))
    if not matched:
        matched = [
            Role.SWE_INTERN,
            Role.DATA_ANALYST,
            Role.FINANCE_ANALYST,
            Role.PRODUCT_MANAGER,
        ]
    return matched


def infer_competency(question: str) -> str:
    lower = question.lower()
    if any(w in lower for w in ("team", "conflict", "collaborat", "disagree")):
        return "collaboration"
    if any(w in lower for w in ("deadline", "pressure", "priorit", "deliver")):
        return "execution"
    if any(w in lower for w in ("adapt", "change", "learn", "fail")):
        return "adaptability"
    if any(w in lower for w in ("problem", "complex", "solve", "initiative")):
        return "problem_solving"
    return "communication"


def parse_ashish_behavioral_markdown(text: str) -> list[str]:
    """Extract question prompts from awesome-behavioral-interviews README."""
    questions: list[str] = []
    seen: set[str] = set()

    summary_tags = re.findall(
        r"<summary>\s*(?:<b>)?\s*(.*?)\s*(?:</b>)?\s*</summary>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for raw in summary_tags:
        line = re.sub(r"<[^>]+>", "", raw).strip()
        if line:
            _normalize_question(line, seen, questions)

    starters = (
        "tell me",
        "describe",
        "why do you",
        "what is",
        "can you",
        "how do you",
        "where do you",
        "give me",
        "walk me",
        "have you",
        "tell us",
        "share an example",
    )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or len(line) > 160 or "<" in line:
            continue
        if line.startswith("#") or line.startswith("|"):
            continue
        if line.startswith("**") and line.endswith("**"):
            line = line.strip("*").strip()

        lower = line.lower()
        if not any(lower.startswith(s) for s in starters):
            continue

        _normalize_question(line, seen, questions)

    return questions


def _normalize_question(line: str, seen: set[str], bucket: list[str] | None = None) -> str | None:
    q = line.strip().rstrip(".")
    if not q.endswith("?"):
        q = f"{q}?"
    key = q.lower()
    if key in seen:
        return None
    seen.add(key)
    if bucket is not None:
        bucket.append(q)
    return q


def load_feed_cache() -> dict:
    if not CACHE_PATH.exists():
        return {"questions": [], "synced_at": None, "sources": []}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"questions": [], "synced_at": None, "sources": []}


def load_external_rubrics() -> list:
    cache = load_feed_cache()
    rubrics = []
    for entry in cache.get("questions", []):
        role = Role(entry["role"])
        rubrics.append(
            make_behavioral_rubric(
                role=role,
                question_id=entry["question_id"],
                question=entry["question"],
            )
        )
    return rubrics


def external_question_meta() -> dict[str, tuple[str, int]]:
    cache = load_feed_cache()
    meta: dict[str, tuple[str, int]] = {}
    for entry in cache.get("questions", []):
        meta[entry["question_id"]] = (
            entry.get("competency", "communication"),
            int(entry.get("difficulty", 3)),
        )
    return meta


def feed_status() -> dict:
    cache = load_feed_cache()
    counts: dict[str, int] = {}
    for entry in cache.get("questions", []):
        role = entry.get("role", "unknown")
        counts[role] = counts.get(role, 0) + 1
    return {
        "synced_at": cache.get("synced_at"),
        "sources": cache.get("sources", []),
        "total": len(cache.get("questions", [])),
        "by_role": counts,
        "cache_path": str(CACHE_PATH),
    }


def build_cache_entries(parsed_questions: list[str], source_name: str) -> list[dict]:
    entries: list[dict] = []
    seen: set[str] = set()
    for question in parsed_questions:
        for role in infer_roles(question):
            qid = _slug(f"{role.value}:{question}", prefix=f"feed_{role.value[:3]}")
            if qid in seen:
                continue
            seen.add(qid)
            entries.append(
                {
                    "question_id": qid,
                    "question": question,
                    "role": role.value,
                    "competency": infer_competency(question),
                    "difficulty": 3,
                    "source": source_name,
                }
            )
    return entries
