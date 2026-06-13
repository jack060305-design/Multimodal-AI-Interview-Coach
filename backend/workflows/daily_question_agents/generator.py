"""Question Generator agent — one LLM call per role (or revision pass for rejected)."""

from __future__ import annotations

import hashlib
import json

from rubrics.external_feed_loader import infer_competency
from schemas import Role
from workflows.daily_question_agents.llm_utils import append_trace, call_llm_json
from workflows.daily_question_agents.state import DailyQuestionState

ROLE_LABELS = {
    Role.SWE_INTERN: "Software Engineering Intern",
    Role.DATA_ANALYST: "Data Analyst",
    Role.FINANCE_ANALYST: "Finance Analyst",
    Role.PRODUCT_MANAGER: "Product Manager",
}

GENERATOR_SYSTEM = """You create high-quality mock interview questions for job candidates.
Output ONLY valid JSON. Questions must be realistic, STAR-friendly, answerable in 2-3 minutes.
Do not repeat questions from the avoid list."""

GENERATOR_USER = """Role: {role_label}
Theme: {theme}
Role angle: {angle}
Target competencies: {competencies}
Count: {count}
Date: {day}

Research brief:
{research_brief}

Avoid duplicating:
{avoid_list}

Return JSON:
{{
  "questions": [
    {{
      "question": "...",
      "competency": "communication|problem_solving|execution|collaboration|adaptability",
      "difficulty": 1-5,
      "ideal_answer_hint": "brief STAR outline"
    }}
  ]
}}"""

REVISION_USER = """Role: {role_label}
Theme: {theme}
Critic feedback: {feedback}

Regenerate exactly {count} improved questions addressing the feedback.
Avoid list: {avoid_list}

Return JSON with "questions" array (same schema as before)."""


def _question_id(role: str, question: str, day: str) -> str:
    digest = hashlib.sha1(f"{day}:{role}:{question}".encode()).hexdigest()[:10]
    return f"llm_{day.replace('-', '')}_{role[:3]}_{digest}"


def _normalize_entry(item: dict, role: Role, day: str, theme: str) -> dict | None:
    question = str(item.get("question", "")).strip()
    if len(question) < 15:
        return None
    if not question.endswith("?"):
        question = f"{question}?"
    competency = str(item.get("competency") or infer_competency(question))
    if competency not in (
        "communication",
        "problem_solving",
        "execution",
        "collaboration",
        "adaptability",
    ):
        competency = infer_competency(question)
    return {
        "question_id": _question_id(role.value, question, day),
        "question": question,
        "role": role.value,
        "competency": competency,
        "difficulty": max(1, min(5, int(item.get("difficulty", 3)))),
        "ideal_answer_hint": str(item.get("ideal_answer_hint", "")).strip(),
        "source": "llm_agentic",
        "generated_on": day,
        "theme": theme,
    }


def _generate_for_role(
    state: DailyQuestionState,
    role: Role,
    count: int,
    feedback: str = "",
) -> list[dict]:
    plan = state.get("plan") or {}
    role_plan = (plan.get("role_plans") or {}).get(role.value, {})
    avoid = state.get("avoid_questions") or []
    avoid_extra = role_plan.get("avoid") or []
    avoid_list = "\n".join(f"- {q}" for q in (avoid[:15] + avoid_extra)[:20]) or "(none)"

    if feedback:
        user = REVISION_USER.format(
            role_label=ROLE_LABELS[role],
            theme=state.get("theme", ""),
            feedback=feedback,
            count=count,
            avoid_list=avoid_list,
        )
    else:
        user = GENERATOR_USER.format(
            role_label=ROLE_LABELS[role],
            theme=state.get("theme", ""),
            angle=role_plan.get("angle", state.get("theme", "")),
            competencies=", ".join(role_plan.get("competencies") or ["communication"]),
            count=count,
            day=state.get("day", ""),
            research_brief=(state.get("research_brief") or "")[:3000],
            avoid_list=avoid_list,
        )

    data = call_llm_json(GENERATOR_SYSTEM, user)
    state["llm_calls"] = int(state.get("llm_calls", 0)) + 1

    entries: list[dict] = []
    seen: set[str] = set()
    for item in data.get("questions", [])[:count]:
        entry = _normalize_entry(item, role, state.get("day", ""), state.get("theme", ""))
        if entry and entry["question"].lower() not in seen:
            seen.add(entry["question"].lower())
            entries.append(entry)
    return entries


def generator_node(state: DailyQuestionState) -> DailyQuestionState:
    state = dict(state)
    per_role = state.get("per_role", 3)
    day = state.get("day", "")
    revision_round = int(state.get("revision_round", 0))
    rejected = state.get("rejected_questions") or []

    if revision_round > 0 and rejected:
        by_role: dict[str, list[dict]] = {}
        for item in rejected:
            by_role.setdefault(item.get("role", ""), []).append(item)

        existing_drafts = {
            q["question_id"]: q for q in (state.get("draft_questions") or [])
        }
        feedback_map = {
            item.get("question_id", ""): item.get("critic_reason", "")
            for item in rejected
        }

        for role in Role:
            role_rejected = by_role.get(role.value, [])
            if not role_rejected:
                continue
            fb = "; ".join(
                feedback_map.get(r.get("question_id", ""), "improve quality")
                for r in role_rejected
            )
            new_entries = _generate_for_role(state, role, len(role_rejected), feedback=fb)
            for old in role_rejected:
                existing_drafts.pop(old.get("question_id", ""), None)
            for entry in new_entries:
                existing_drafts[entry["question_id"]] = entry

        state["draft_questions"] = list(existing_drafts.values())
        state["rejected_questions"] = []
        append_trace(
            state,
            "generator",
            f"revision={revision_round}; drafts={len(state['draft_questions'])}; llm={state.get('llm_calls', 0)}",
        )
        return state

    drafts: list[dict] = list(state.get("draft_questions") or [])
    existing_ids = {d["question_id"] for d in drafts}

    for role in Role:
        try:
            entries = _generate_for_role(state, role, per_role)
            for entry in entries:
                if entry["question_id"] not in existing_ids:
                    drafts.append(entry)
                    existing_ids.add(entry["question_id"])
        except Exception as exc:
            errors = list(state.get("errors", []))
            errors.append(f"generator:{role.value}: {exc}")
            state["errors"] = errors

    state["draft_questions"] = drafts
    append_trace(
        state,
        "generator",
        f"drafts={len(drafts)}; llm_calls={state.get('llm_calls', 0)}",
    )
    return state
