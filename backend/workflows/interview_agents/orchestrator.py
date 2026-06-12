"""
Friday-inspired 5-agent turn orchestrator (Interviewer / Grader / Clarifier / Followup / Coach).
Pattern reference: https://github.com/mostofashakib/Friday
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from workflows.interview_agents.clarifier import clarifier_node
from workflows.interview_agents.coach import coach_node
from workflows.interview_agents.followup import followup_node
from workflows.interview_agents.grader import grader_node
from workflows.interview_agents.interviewer import interviewer_node
from workflows.interview_agents.question_bank import get_question_by_id
from workflows.interview_agents.routing import route_after_followup, route_after_grader
from workflows.interview_agents.session_memory import record_turn_embedding
from workflows.interview_agents.state import InterviewState


@dataclass
class TurnResult:
    grading: dict[str, Any]
    coaching_note: str
    question: str | None
    question_id: str | None
    competency: str | None
    is_followup: bool
    route: str
    session_complete: bool
    difficulty: int
    turn_number: int
    trace: list[dict[str, str]] = field(default_factory=list)
    immediate_followup: bool = False


async def run_first_question(state: InterviewState) -> InterviewState:
    state = dict(state)
    state["agent_trace"] = []

    locked_id = state.get("first_question_id")
    if locked_id:
        picked = get_question_by_id(state["role"], locked_id)
        if picked:
            asked = list(state.get("asked_question_ids", []))
            if picked.question_id not in asked:
                asked.append(picked.question_id)
            state.update(
                {
                    "current_question": picked.question,
                    "current_question_id": picked.question_id,
                    "current_competency": picked.competency,
                    "asked_question_ids": asked,
                    "turn_number": 1,
                }
            )
            state["agent_trace"].append(
                {
                    "node": "interviewer",
                    "decision": f"opening '{picked.question_id}' from bank (preview lock)",
                }
            )
            return state

    state.update(await interviewer_node(state))
    state["turn_number"] = 1
    state["agent_trace"].append(
        {"node": "interviewer", "decision": "opening question from bank"}
    )
    return state


async def run_turn(state: InterviewState) -> TurnResult:
    state = dict(state)
    state["clarifier_active"] = False
    state["follow_up_needed"] = False
    state["follow_up_question"] = ""
    state["agent_trace"] = []
    trace = state["agent_trace"]

    state.update(await grader_node(state))
    grading = state["grading"]
    score = int(grading.get("score", 3))
    competency = grading.get("competency", state.get("current_competency", "general"))
    trace.append({"node": "grader", "decision": f"score={score}, competency={competency}"})

    state["turn_embeddings"] = record_turn_embedding(
        state.get("turn_embeddings", []),
        question=state.get("current_question", ""),
        answer=state.get("current_answer", ""),
        competency=competency,
        score=score,
    )

    state.setdefault("messages", []).extend(
        [
            {
                "role": "interviewer",
                "turn_number": state.get("turn_number", 0),
                "content": state.get("current_question", ""),
                "competency": state.get("current_competency"),
            },
            {
                "role": "user",
                "turn_number": state.get("turn_number", 0),
                "content": state.get("current_answer", ""),
                "competency": competency,
                "feedback": grading.get("feedback", ""),
            },
        ]
    )

    branch = route_after_grader(state)
    trace.append({"node": "router", "decision": f"score={score} → {branch}"})

    if branch == "clarifier":
        state.update(await clarifier_node(state))
        trace.append({"node": "clarifier", "decision": f"probe weak area '{competency}'"})

    elif branch == "followup":
        state.update(await followup_node(state))
        trace.append(
            {
                "node": "followup",
                "decision": (
                    "RAG gap → targeted follow-up"
                    if state.get("follow_up_needed")
                    else "no gap → coach"
                ),
            }
        )
        follow_route = route_after_followup(state)
        trace.append({"node": "router", "decision": f"followup → {follow_route}"})

        if follow_route == "interviewer":
            state.update(await interviewer_node(state))
            trace.append({"node": "interviewer", "decision": "immediate follow-up"})
            return TurnResult(
                grading=grading,
                coaching_note="",
                question=state["current_question"],
                question_id=state.get("current_question_id"),
                competency=state.get("current_competency"),
                is_followup=True,
                route="followup",
                session_complete=False,
                difficulty=state.get("difficulty", 3),
                turn_number=state.get("turn_number", 0),
                trace=trace,
                immediate_followup=True,
            )

    old_difficulty = state.get("difficulty", 3)
    state.update(await coach_node(state))
    trace.append(
        {
            "node": "coach",
            "decision": (
                f"difficulty {old_difficulty}→{state['difficulty']}, "
                f"complete={state['session_complete']}"
            ),
        }
    )

    if state.get("session_complete"):
        return TurnResult(
            grading=grading,
            coaching_note=state["coaching_notes"][-1] if state.get("coaching_notes") else "",
            question=None,
            question_id=None,
            competency=None,
            is_followup=branch == "clarifier",
            route=branch,
            session_complete=True,
            difficulty=state.get("difficulty", 3),
            turn_number=state.get("turn_number", 0),
            trace=trace,
        )

    state["turn_number"] = state.get("turn_number", 0) + 1
    state.update(await interviewer_node(state))
    trace.append(
        {
            "node": "interviewer",
            "decision": (
                f"clarifier probe for '{competency}'"
                if branch == "clarifier"
                else f"next question @ difficulty {state['difficulty']}"
            ),
        }
    )

    return TurnResult(
        grading=grading,
        coaching_note=state["coaching_notes"][-1] if state.get("coaching_notes") else "",
        question=state["current_question"],
        question_id=state.get("current_question_id"),
        competency=state.get("current_competency"),
        is_followup=branch == "clarifier",
        route=branch,
        session_complete=False,
        difficulty=state.get("difficulty", 3),
        turn_number=state.get("turn_number", 0),
        trace=trace,
    )
