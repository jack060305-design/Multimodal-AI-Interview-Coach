"""Role-based question bank (Friday-style) backed by rubrics + external feeds."""

from __future__ import annotations

import random
from dataclasses import dataclass

from rubrics.bank_rubrics import BANK_QUESTION_META, BANK_RUBRICS
from rubrics.external_feed_loader import external_question_meta
from rubrics.job_search_rubrics import JOB_SEARCH_META
from rubrics.llm_daily_loader import llm_daily_question_meta, llm_daily_question_sources
from rubrics.sample_rubrics import SAMPLE_RUBRICS
from schemas import Role


@dataclass(frozen=True)
class BankQuestion:
    question_id: str
    question: str
    competency: str
    difficulty: int
    role: Role
    source: str = "local"


def _question_meta() -> dict[str, tuple[str, int]]:
    meta = dict(BANK_QUESTION_META)
    meta.update(JOB_SEARCH_META)
    meta.update(external_question_meta())
    meta.update(llm_daily_question_meta())
    return meta


def _competency_from_rubric(doc) -> str:
    if doc.rubric:
        return doc.rubric[0].criterion.lower().replace(" ", "_")[:48]
    return "general"


def _source_for(doc) -> str:
    qid = doc.question_id
    if qid.startswith("feed_"):
        return "external_feed"
    if qid.startswith("llm_"):
        return llm_daily_question_sources().get(qid, "llm_daily")
    if qid.endswith("_job_") or "_job_" in qid:
        return "job_search"
    if qid in BANK_QUESTION_META:
        return "langgraph_bank"
    return "core_rubric"


def _build_bank() -> dict[str, dict[str, list[BankQuestion]]]:
    bank: dict[str, dict[str, list[BankQuestion]]] = {}
    meta = _question_meta()
    seen: set[tuple[str, str]] = set()

    for doc in SAMPLE_RUBRICS:
        role_key = doc.role.value
        key = (role_key, doc.question_id)
        if key in seen:
            continue
        seen.add(key)

        if doc.question_id in meta:
            competency, difficulty = meta[doc.question_id]
        else:
            competency = _competency_from_rubric(doc)
            difficulty = 3

        bank.setdefault(role_key, {}).setdefault(competency, []).append(
            BankQuestion(
                question_id=doc.question_id,
                question=doc.question,
                competency=competency,
                difficulty=difficulty,
                role=doc.role,
                source=_source_for(doc),
            )
        )

    return bank


QUESTION_BANK = _build_bank()
DEFAULT_QUESTION_BUDGET = 2


def reload_bank() -> dict[str, int]:
    """Rebuild runtime bank after rubric/feed reload."""
    global QUESTION_BANK
    QUESTION_BANK = _build_bank()
    return {role: len(all_questions_for_role(role)) for role in QUESTION_BANK}


def competencies_for_role(role: str) -> list[str]:
    return list(QUESTION_BANK.get(role, {}).keys())


def initial_question_budget(role: str) -> dict[str, int]:
    return {c: DEFAULT_QUESTION_BUDGET for c in competencies_for_role(role)}


def get_question_by_id(role: str, question_id: str) -> BankQuestion | None:
    for questions in QUESTION_BANK.get(role, {}).values():
        for q in questions:
            if q.question_id == question_id:
                return q
    return None


def all_questions_for_role(role: str) -> list[BankQuestion]:
    return [q for questions in QUESTION_BANK.get(role, {}).values() for q in questions]


def pick_random_preview(
    role: str,
    difficulty: int = 3,
    exclude_ids: list[str] | None = None,
) -> BankQuestion | None:
    """Random question from the role bank (preview / shuffle before interview starts)."""
    exclude = set(exclude_ids or [])
    pool = [q for q in all_questions_for_role(role) if q.question_id not in exclude]
    if not pool:
        pool = all_questions_for_role(role)
    if not pool:
        return None

    level = max(1, min(5, difficulty))
    near = [q for q in pool if abs(q.difficulty - level) <= 1]
    return random.choice(near or pool)


def session_rng(state: dict) -> random.Random:
    """Deterministic per session so the same turn does not reshuffle questions."""
    seed = state.get("session_id") or state.get("role") or "default"
    turn = int(state.get("turn_number", 0))
    return random.Random(f"{seed}:{turn}:{len(state.get('asked_question_ids', []))}")


def search_question_bank(
    role: str,
    competency: str,
    difficulty: int,
    exclude_ids: list[str] | None = None,
    rng: random.Random | None = None,
) -> BankQuestion | None:
    exclude = set(exclude_ids or [])
    comp_bank = QUESTION_BANK.get(role, {}).get(competency, [])
    level = max(1, min(5, difficulty))
    candidates = [
        q
        for q in comp_bank
        if q.question_id not in exclude and abs(q.difficulty - level) <= 1
    ]
    if not candidates:
        candidates = [q for q in comp_bank if q.question_id not in exclude]
    if not candidates:
        return None
    picker = rng or random
    return picker.choice(candidates)


def pick_competency(state: dict) -> str:
    role = state["role"]
    budget = state.get("question_budget", {})
    banned = set(state.get("banned_competencies", []))
    scores = state.get("competency_scores", {})
    rng = session_rng(state)

    available = [c for c, n in budget.items() if n > 0 and c not in banned]
    if not available:
        return competencies_for_role(role)[0] if competencies_for_role(role) else "general"

    untested = [c for c in available if c not in scores]
    if untested:
        return rng.choice(untested)

    weak = [c for c in available if scores.get(c, 5) < 3.5]
    if weak:
        return rng.choice(weak)

    return rng.choice(available)


def get_competency_history(state: dict, competency: str) -> str:
    scores = state.get("competency_scores", {})
    msgs = state.get("messages", [])
    relevant = [m for m in msgs if m.get("competency") == competency and m.get("role") == "user"]

    lines = [f"Competency: {competency}"]
    if competency in scores:
        lines.append(f"Rolling score: {scores[competency]:.1f}/5")
    lines.append(f"Questions asked on this topic: {len(relevant)}")
    return "\n".join(lines)
