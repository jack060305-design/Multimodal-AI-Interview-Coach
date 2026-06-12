from __future__ import annotations

from schemas import EvaluationResult, Role
from services.orchestrator import EvaluationOrchestrator
from workflows.interview_agents import run_first_question, run_turn, session_store
from workflows.interview_agents.question_bank import pick_random_preview
from workflows.interview_agents.orchestrator import TurnResult


class InterviewSessionService:
    def create_session(
        self,
        role: str,
        max_turns: int = 5,
        difficulty: int = 3,
        first_question_id: str | None = None,
    ) -> dict:
        state = session_store.create(
            role=role,
            max_turns=max_turns,
            difficulty=difficulty,
            first_question_id=first_question_id,
        )
        return {
            "session_id": state["session_id"],
            "role": role,
            "max_turns": max_turns,
            "difficulty": difficulty,
        }

    async def start(self, session_id: str) -> dict:
        state = session_store.get(session_id)
        if not state:
            raise ValueError("Session not found")
        if state.get("current_question"):
            return self._question_payload(state)

        state = await run_first_question(state)
        session_store.save(state)
        return self._question_payload(state)

    async def submit_answer(self, session_id: str, answer: str) -> dict:
        state = session_store.get(session_id)
        if not state:
            raise ValueError("Session not found")
        if state.get("session_complete"):
            raise ValueError("Session already complete")

        state["current_answer"] = answer.strip()
        if not state["current_answer"]:
            raise ValueError("Answer required")

        result: TurnResult = await run_turn(state)
        self._apply_turn_result(state, result)
        session_store.save(state)
        return self._turn_payload(result)

    async def submit_video_turn(
        self,
        session_id: str,
        video_bytes: bytes,
        filename: str,
        orchestrator: EvaluationOrchestrator,
        gpu_consent: str | None = None,
    ) -> dict:
        state = session_store.get(session_id)
        if not state:
            raise ValueError("Session not found")
        if state.get("session_complete"):
            raise ValueError("Session already complete")

        role = Role(state["role"])
        question = state["current_question"]
        question_id = state.get("current_question_id") or None

        evaluation: EvaluationResult = orchestrator.evaluate_upload(
            file_bytes=video_bytes,
            filename=filename,
            role=role,
            question=question,
            question_id=question_id,
            gpu_consent=gpu_consent,
        )

        state["current_answer"] = evaluation.transcript.strip()
        if not state["current_answer"]:
            raise ValueError("Could not transcribe speech from the recording.")

        result: TurnResult = await run_turn(state)
        self._apply_turn_result(state, result)
        session_store.save(state)

        return {
            "transcript": evaluation.transcript,
            "evaluation": evaluation,
            **self._turn_payload(result),
        }

    def random_preview(self, role: str, difficulty: int = 3) -> dict:
        picked = pick_random_preview(role=role, difficulty=difficulty)
        if not picked:
            raise ValueError(f"No questions in bank for role={role}")
        return {
            "role": role,
            "question_id": picked.question_id,
            "question": picked.question,
            "competency": picked.competency,
            "difficulty": picked.difficulty,
            "source": "langgraph_bank",
        }

    def get_session(self, session_id: str) -> dict | None:
        return session_store.summary(session_id)

    def _apply_turn_result(self, state: dict, result: TurnResult) -> None:
        state["grading"] = result.grading
        state["session_complete"] = result.session_complete
        state["difficulty"] = result.difficulty
        state["turn_number"] = result.turn_number
        if result.question:
            state["current_question"] = result.question
            if result.question_id:
                state["current_question_id"] = result.question_id
            if result.competency:
                state["current_competency"] = result.competency
        state["agent_trace"] = result.trace

    def _turn_payload(self, result: TurnResult) -> dict:
        return {
            "grading": result.grading,
            "coaching_note": result.coaching_note,
            "next_question": result.question,
            "next_question_id": result.question_id,
            "competency": result.competency,
            "is_followup": result.is_followup,
            "route": result.route,
            "session_complete": result.session_complete,
            "difficulty": result.difficulty,
            "turn_number": result.turn_number,
            "agent_trace": result.trace,
        }

    def _question_payload(self, state: dict) -> dict:
        return {
            "session_id": state["session_id"],
            "question": state["current_question"],
            "question_id": state.get("current_question_id"),
            "competency": state.get("current_competency"),
            "difficulty": state.get("difficulty", 3),
            "turn_number": state.get("turn_number", 1),
            "agent_trace": state.get("agent_trace", []),
        }
