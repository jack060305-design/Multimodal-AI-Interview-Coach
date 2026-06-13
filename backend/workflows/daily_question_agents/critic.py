"""Critic/Evaluator agent — one batch LLM call to approve or reject drafts."""

from __future__ import annotations

import json

from workflows.daily_question_agents.llm_utils import append_trace, call_llm_json
from workflows.daily_question_agents.state import DailyQuestionState

CRITIC_SYSTEM = """You are a senior interviewer reviewing mock interview questions.
Output ONLY valid JSON. Reject duplicates, vague prompts, or off-theme questions.
Approve questions that are specific, role-appropriate, and STAR-friendly."""

CRITIC_USER = """Theme: {theme}
Date: {day}

Review these draft questions:
{drafts_json}

Avoid duplicating these existing questions:
{avoid_list}

Return JSON:
{{
  "approved_ids": ["question_id", ...],
  "rejected": [
    {{"question_id": "...", "reason": "too generic / duplicate / off-theme"}}
  ],
  "summary": "one-line quality assessment"
}}"""


def critic_node(state: DailyQuestionState) -> DailyQuestionState:
    state = dict(state)
    drafts = state.get("draft_questions") or []
    if not drafts:
        state["approved_questions"] = []
        state["rejected_questions"] = []
        append_trace(state, "critic", "no drafts to review")
        return state

    avoid = state.get("avoid_questions") or []
    avoid_list = "\n".join(f"- {q}" for q in avoid[:15]) or "(none)"

    compact_drafts = [
        {
            "question_id": d["question_id"],
            "role": d["role"],
            "question": d["question"],
            "competency": d.get("competency"),
            "difficulty": d.get("difficulty"),
        }
        for d in drafts
    ]

    user = CRITIC_USER.format(
        theme=state.get("theme", ""),
        day=state.get("day", ""),
        drafts_json=json.dumps(compact_drafts, ensure_ascii=False, indent=2),
        avoid_list=avoid_list,
    )
    data = call_llm_json(CRITIC_SYSTEM, user)
    state["llm_calls"] = int(state.get("llm_calls", 0)) + 1

    approved_ids = set(data.get("approved_ids") or [])
    rejected_raw = data.get("rejected") or []
    reject_reasons = {
        r.get("question_id", ""): r.get("reason", "quality")
        for r in rejected_raw
        if r.get("question_id")
    }

    if not approved_ids and not reject_reasons:
        approved_ids = {d["question_id"] for d in drafts}

    approved: list[dict] = []
    rejected: list[dict] = []
    for draft in drafts:
        qid = draft["question_id"]
        if qid in approved_ids:
            approved.append(draft)
        elif qid in reject_reasons:
            item = dict(draft)
            item["critic_reason"] = reject_reasons[qid]
            rejected.append(item)
        else:
            approved.append(draft)

    state["approved_questions"] = approved
    state["rejected_questions"] = rejected
    state["critic_notes"] = data.get("summary", "")
    append_trace(
        state,
        "critic",
        f"approved={len(approved)}; rejected={len(rejected)}; llm={state.get('llm_calls', 0)}",
    )
    return state
