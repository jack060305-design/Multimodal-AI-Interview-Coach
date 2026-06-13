"""Planner agent — one LLM call to plan daily themes and role focus areas."""

from __future__ import annotations

import json
from datetime import date

from schemas import Role
from workflows.daily_question_agents.llm_utils import append_trace, call_llm_json
from workflows.daily_question_agents.state import DailyQuestionState

PLANNER_SYSTEM = """You are a mock-interview curriculum planner.
Output ONLY valid JSON. Keep plans concise to minimize token cost."""

PLANNER_USER = """Date: {today}
Base theme rotation: {base_theme}
Questions needed per role: {per_role}

Roles: SWE Intern, Data Analyst, Finance Analyst, Product Manager

Create a focused daily plan. Each role gets a distinct angle on the theme.

Return JSON:
{{
  "theme": "one-line theme for today",
  "rationale": "why this theme fits today",
  "role_plans": {{
    "swe_intern": {{"angle": "...", "competencies": ["communication", "problem_solving"], "avoid": ["generic tell me about yourself"]}},
    "data_analyst": {{"angle": "...", "competencies": [...], "avoid": [...]}},
    "finance_analyst": {{"angle": "...", "competencies": [...], "avoid": [...]}},
    "product_manager": {{"angle": "...", "competencies": [...], "avoid": [...]}}
  }}
}}"""

WEEKLY_THEMES = [
    "teamwork and conflict resolution",
    "handling pressure and tight deadlines",
    "learning from failure and adaptability",
    "communication with non-technical stakeholders",
    "prioritization and trade-offs",
    "leadership and initiative",
    "AI and industry trends in the workplace",
]


def _base_theme() -> str:
    return WEEKLY_THEMES[date.today().toordinal() % len(WEEKLY_THEMES)]


def planner_node(state: DailyQuestionState) -> DailyQuestionState:
    state = dict(state)
    today = state.get("day") or date.today().isoformat()
    per_role = state.get("per_role", 3)
    base_theme = _base_theme()

    user = PLANNER_USER.format(today=today, base_theme=base_theme, per_role=per_role)
    data = call_llm_json(PLANNER_SYSTEM, user)
    state["llm_calls"] = int(state.get("llm_calls", 0)) + 1

    role_plans = data.get("role_plans") or {}
    for role in Role:
        if role.value not in role_plans:
            role_plans[role.value] = {
                "angle": base_theme,
                "competencies": ["communication", "problem_solving"],
                "avoid": [],
            }

    state["plan"] = {
        "theme": data.get("theme") or base_theme,
        "rationale": data.get("rationale", ""),
        "role_plans": role_plans,
        "base_theme": base_theme,
    }
    state["theme"] = state["plan"]["theme"]
    append_trace(
        state,
        "planner",
        f"theme={state['theme'][:60]}; roles={len(role_plans)}",
    )
    return state
