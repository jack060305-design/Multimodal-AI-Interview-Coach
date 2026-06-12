"""Role-based question bank (Friday-style) backed by rubrics + extra prompts."""

from __future__ import annotations

import random
from dataclasses import dataclass

from rubrics.sample_rubrics import SAMPLE_RUBRICS
from schemas import Role


@dataclass(frozen=True)
class BankQuestion:
    question_id: str
    question: str
    competency: str
    difficulty: int
    role: Role


def _competency_from_rubric(doc) -> str:
    if doc.rubric:
        return doc.rubric[0].criterion.lower().replace(" ", "_")[:48]
    return "general"


def _build_bank() -> dict[str, dict[str, list[BankQuestion]]]:
    bank: dict[str, dict[str, list[BankQuestion]]] = {}

    for doc in SAMPLE_RUBRICS:
        role_key = doc.role.value
        competency = _competency_from_rubric(doc)
        bank.setdefault(role_key, {}).setdefault(competency, []).append(
            BankQuestion(
                question_id=doc.question_id,
                question=doc.question,
                competency=competency,
                difficulty=3,
                role=doc.role,
            )
        )

    extras: dict[str, list[tuple[str, str, int, str]]] = {
        Role.SWE_INTERN.value: [
            ("swe_intern_debug_001", "How do you approach debugging a production issue?", 2, "problem_solving"),
            ("swe_intern_git_001", "Explain a merge conflict and how you resolved one.", 2, "collaboration"),
            ("swe_intern_tradeoff_001", "Describe a time you chose a simpler solution over a clever one.", 3, "execution"),
        ],
        Role.DATA_ANALYST.value: [
            ("da_metrics_001", "How do you define and validate a product metric?", 3, "problem_solving"),
            ("da_ab_test_001", "Walk through how you would design an A/B test.", 3, "execution"),
            ("da_stakeholder_001", "Tell me about presenting insights to a non-technical stakeholder.", 2, "communication"),
        ],
        Role.FINANCE_ANALYST.value: [
            ("fa_variance_001", "How do you explain a budget variance to leadership?", 2, "communication"),
            ("fa_model_001", "What checks do you run before sharing a financial model?", 3, "execution"),
            ("fa_assumption_001", "Describe a time a key assumption in your analysis was wrong.", 3, "adaptability"),
        ],
        Role.PRODUCT_MANAGER.value: [
            ("pm_discovery_001", "How do you run discovery when requirements are ambiguous?", 3, "problem_solving"),
            ("pm_roadmap_001", "Describe balancing tech debt against new features.", 3, "execution"),
            ("pm_conflict_001", "Tell me about aligning engineering and sales on priorities.", 3, "collaboration"),
        ],
    }

    for role_key, items in extras.items():
        role = Role(role_key)
        for qid, text, diff, comp in items:
            bank.setdefault(role_key, {}).setdefault(comp, []).append(
                BankQuestion(
                    question_id=qid,
                    question=text,
                    competency=comp,
                    difficulty=diff,
                    role=role,
                )
            )

    return bank


QUESTION_BANK = _build_bank()
DEFAULT_QUESTION_BUDGET = 2


def competencies_for_role(role: str) -> list[str]:
    return list(QUESTION_BANK.get(role, {}).keys())


def initial_question_budget(role: str) -> dict[str, int]:
    return {c: DEFAULT_QUESTION_BUDGET for c in competencies_for_role(role)}


def search_question_bank(
    role: str,
    competency: str,
    difficulty: int,
    exclude_ids: list[str] | None = None,
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
    return random.choice(candidates)


def pick_competency(state: dict) -> str:
    role = state["role"]
    budget = state.get("question_budget", {})
    banned = set(state.get("banned_competencies", []))
    scores = state.get("competency_scores", {})

    available = [c for c, n in budget.items() if n > 0 and c not in banned]
    if not available:
        return competencies_for_role(role)[0] if competencies_for_role(role) else "general"

    untested = [c for c in available if c not in scores]
    if untested:
        return random.choice(untested)

    weak = [c for c in available if scores.get(c, 5) < 3.5]
    if weak:
        return random.choice(weak)

    return random.choice(available)


def get_competency_history(state: dict, competency: str) -> str:
    scores = state.get("competency_scores", {})
    msgs = state.get("messages", [])
    relevant = [m for m in msgs if m.get("competency") == competency and m.get("role") == "user"]

    lines = [f"Competency: {competency}"]
    if competency in scores:
        lines.append(f"Rolling score: {scores[competency]:.1f}/5")
    lines.append(f"Questions asked on this topic: {len(relevant)}")
    return "\n".join(lines)
