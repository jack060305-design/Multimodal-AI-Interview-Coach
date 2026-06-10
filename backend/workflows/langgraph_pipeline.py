from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from processors import AudioAnalyzer, CVAnalyzer, VideoProcessor, create_transcriber
from rubric_engine.evaluator import RubricEvaluator
from rubric_engine.store_factory import get_vector_store
from schemas import (
    EvaluationMetrics,
    EvaluationResult,
    PerformanceCategory,
    PerformanceSummary,
    Role,
)


class GraphState(TypedDict, total=False):
    video_path: str
    role: Role
    question: str
    question_id: str | None
    artifacts: Any
    transcript: Any
    eye_contact: Any
    filler: Any
    confidence: Any
    rubric_payload: dict
    llm_result: dict
    result: EvaluationResult


class EvaluationGraph:
    """LangGraph workflow for multimodal interview evaluation."""

    def __init__(self):
        self.video_processor = VideoProcessor()
        self.cv_analyzer = CVAnalyzer()
        self.audio_analyzer = AudioAnalyzer()
        self.vector_store = get_vector_store()
        self.evaluator = RubricEvaluator()
        self.graph = self._build()

    def _build(self):
        g = StateGraph(GraphState)
        g.add_node("extract_media", self._extract_media)
        g.add_node("transcribe", self._transcribe)
        g.add_node("analyze_vision", self._analyze_vision)
        g.add_node("analyze_audio", self._analyze_audio)
        g.add_node("retrieve_rubric", self._retrieve_rubric)
        g.add_node("llm_evaluate", self._llm_evaluate)
        g.add_node("aggregate", self._aggregate)

        g.set_entry_point("extract_media")
        g.add_edge("extract_media", "transcribe")
        g.add_edge("transcribe", "analyze_vision")
        g.add_edge("analyze_vision", "analyze_audio")
        g.add_edge("analyze_audio", "retrieve_rubric")
        g.add_edge("retrieve_rubric", "llm_evaluate")
        g.add_edge("llm_evaluate", "aggregate")
        g.add_edge("aggregate", END)
        return g.compile()

    def run(
        self,
        video_path: str,
        role: Role,
        question: str,
        question_id: str | None = None,
    ) -> EvaluationResult:
        final = self.graph.invoke(
            {
                "video_path": video_path,
                "role": role,
                "question": question,
                "question_id": question_id,
            }
        )
        return final["result"]

    def _extract_media(self, state: GraphState) -> GraphState:
        state["artifacts"] = self.video_processor.process(state["video_path"])
        return state

    def _transcribe(self, state: GraphState) -> GraphState:
        transcriber = create_transcriber()
        state["transcript"] = transcriber.transcribe(
            str(state["artifacts"].audio_path)
        )
        return state

    def _analyze_vision(self, state: GraphState) -> GraphState:
        state["eye_contact"] = self.cv_analyzer.analyze_frames(
            state["artifacts"].frames_dir
        )
        return state

    def _analyze_audio(self, state: GraphState) -> GraphState:
        filler, confidence = self.audio_analyzer.analyze(
            str(state["artifacts"].audio_path),
            state["transcript"],
            state["eye_contact"].score,
        )
        state["filler"] = filler
        state["confidence"] = confidence
        return state

    def _retrieve_rubric(self, state: GraphState) -> GraphState:
        role = state["role"]
        question = state["question"]
        question_id = state.get("question_id")

        payload = None
        if question_id:
            payload = self.vector_store.get_by_question_id(role, question_id)
        if not payload:
            retrieved = self.vector_store.retrieve(role, question, k=1)
            payload = retrieved[0] if retrieved else None
        if not payload:
            raise ValueError(
                f"No rubric found for role={role.value} question={question!r}"
            )
        state["rubric_payload"] = payload
        return state

    def _llm_evaluate(self, state: GraphState) -> GraphState:
        state["llm_result"] = self.evaluator.evaluate(
            state["role"],
            state["transcript"],
            state["rubric_payload"],
        )
        return state

    def _aggregate(self, state: GraphState) -> GraphState:
        eye = state["eye_contact"]
        filler = state["filler"]
        confidence = state["confidence"]
        llm = state["llm_result"]
        rubric = state["rubric_payload"]

        delivery_score = int(round((eye.score + confidence.score) / 2))
        communication_score = int(
            round((filler.score + llm["response_quality"].score) / 2)
        )
        technical_score = llm["technical_depth"].score

        behavioral_avg = (eye.score + filler.score + confidence.score) / 3
        content_avg = (llm["technical_depth"].score + llm["response_quality"].score) / 2
        overall = int(round(behavioral_avg * 0.45 + content_avg * 0.55))

        suggestions = list(llm.get("improvement_suggestions", []))
        if filler.rate > 5:
            suggestions.append(
                f"Reduce filler words — top: {', '.join(filler.top_fillers) or 'none'} "
                f"({filler.rate}%)."
            )
        if eye.percentage < 60:
            suggestions.append(
                f"Increase eye contact — {eye.percentage}% (target 80%+)."
            )

        import uuid

        state["result"] = EvaluationResult(
            evaluation_id=uuid.uuid4(),
            overall_score=overall,
            role=state["role"],
            question=rubric["question"],
            question_id=rubric["question_id"],
            transcript=state["transcript"].text,
            performance=PerformanceSummary(
                delivery=PerformanceCategory(
                    score=delivery_score,
                    label="Delivery",
                    summary="Eye contact, confidence, and on-camera presence.",
                    signals=["eye_contact", "confidence", "posture"],
                ),
                communication=PerformanceCategory(
                    score=communication_score,
                    label="Communication",
                    summary="Clarity, pacing, filler words, and response structure.",
                    signals=["filler_words", "response_quality", "wpm"],
                ),
                technical_depth=PerformanceCategory(
                    score=technical_score,
                    label="Technical Depth",
                    summary="Rubric-grounded content accuracy and depth.",
                    signals=["technical_depth"],
                ),
            ),
            metrics=EvaluationMetrics(
                eye_contact=eye,
                filler_words=filler,
                confidence=confidence,
                technical_depth=llm["technical_depth"],
                response_quality=llm["response_quality"],
            ),
            improvement_suggestions=suggestions,
        )
        return state
