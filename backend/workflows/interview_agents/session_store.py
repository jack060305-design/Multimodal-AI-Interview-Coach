from __future__ import annotations

import uuid
from threading import Lock
from typing import Any

from workflows.interview_agents.question_bank import initial_question_budget
from workflows.interview_agents.state import InterviewState


class InterviewSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, InterviewState] = {}
        self._lock = Lock()

    def create(
        self,
        role: str,
        max_turns: int = 5,
        difficulty: int = 3,
        first_question_id: str | None = None,
    ) -> InterviewState:
        session_id = str(uuid.uuid4())
        state: InterviewState = {
            "session_id": session_id,
            "role": role,
            "difficulty": difficulty,
            "max_turns": max_turns,
            "turn_number": 0,
            "current_question": "",
            "current_question_id": "",
            "current_competency": "",
            "current_answer": "",
            "grading": {},
            "competency_scores": {},
            "question_budget": initial_question_budget(role),
            "banned_competencies": [],
            "coach_directives": [],
            "coaching_notes": [],
            "follow_up_needed": False,
            "follow_up_question": "",
            "clarifier_active": False,
            "session_complete": False,
            "messages": [],
            "turn_embeddings": [],
            "asked_question_ids": [],
            "agent_trace": [],
            "first_question_id": first_question_id or "",
        }
        with self._lock:
            self._sessions[session_id] = state
        return state

    def get(self, session_id: str) -> InterviewState | None:
        with self._lock:
            s = self._sessions.get(session_id)
            return dict(s) if s else None

    def save(self, state: InterviewState) -> None:
        sid = state.get("session_id")
        if not sid:
            return
        with self._lock:
            self._sessions[sid] = dict(state)

    def summary(self, session_id: str) -> dict[str, Any] | None:
        state = self.get(session_id)
        if not state:
            return None
        return {
            "session_id": session_id,
            "role": state["role"],
            "difficulty": state.get("difficulty", 3),
            "turn_number": state.get("turn_number", 0),
            "session_complete": state.get("session_complete", False),
            "competency_scores": state.get("competency_scores", {}),
            "coaching_notes": state.get("coaching_notes", []),
            "messages": state.get("messages", []),
        }


session_store = InterviewSessionStore()
