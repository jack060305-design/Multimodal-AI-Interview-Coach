from typing import Any, TypedDict


class InterviewState(TypedDict, total=False):
    session_id: str
    role: str
    difficulty: int
    max_turns: int
    turn_number: int

    current_question: str
    current_question_id: str
    current_competency: str
    current_answer: str
    precomputed_grading: dict[str, Any]

    grading: dict[str, Any]
    competency_scores: dict[str, float]
    question_budget: dict[str, int]
    banned_competencies: list[str]
    coach_directives: list[str]
    coaching_notes: list[str]

    follow_up_needed: bool
    follow_up_question: str
    clarifier_active: bool
    session_complete: bool

    messages: list[dict[str, Any]]
    turn_embeddings: list[dict[str, Any]]
    asked_question_ids: list[str]
    agent_trace: list[dict[str, str]]
