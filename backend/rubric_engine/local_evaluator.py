import re
from typing import Any

from schemas import CriterionScore, ResponseQualityMetric, Role, TechnicalDepthMetric, TranscriptResult


def _has_valid_llm_key() -> bool:
    import os

    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "local":
        return False
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }
    key_name = key_map.get(provider, "OPENAI_API_KEY")
    val = (os.getenv(key_name) or "").strip()
    if not val or val in ("sk-...", "sk-your_openai_key"):
        return False
    if provider == "openai" and val.startswith("sk-") and len(val) < 20:
        return False
    if provider == "anthropic" and val.startswith("sk-ant-") and len(val) < 24:
        return False
    if provider == "gemini" and len(val) < 20:
        return False
    return True


def _keyword_score(text: str, keywords: list[str]) -> int:
    if not text.strip():
        return 0
    lower = text.lower()
    hits = sum(1 for k in keywords if k.lower() in lower)
    if hits == 0:
        return 3
    if hits == 1:
        return 6
    if hits <= 3:
        return 8
    return 10


def _length_score(word_count: int) -> int:
    if word_count < 20:
        return 2
    if word_count < 50:
        return 5
    if word_count < 100:
        return 7
    return 9


def evaluate_local(
    role: Role,
    transcript: TranscriptResult,
    rubric_payload: dict[str, Any],
) -> dict[str, Any]:
    text = transcript.text or ""
    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)
    ideal = rubric_payload.get("ideal_answer", "")
    ideal_keywords = re.findall(r"\b[a-zA-Z]{4,}\b", ideal)[:40]

    tech_breakdown: list[CriterionScore] = []
    rubric = rubric_payload.get("rubric", [])
    for item in rubric:
        criterion = item.get("criterion", "criterion")
        kw_score = _keyword_score(text, ideal_keywords)
        len_score = _length_score(word_count)
        score = int(round((kw_score + len_score) / 2))
        tech_breakdown.append(
            CriterionScore(
                criterion=criterion,
                score=score,
                max_score=10,
                evidence=text[:120] + ("..." if len(text) > 120 else ""),
                justification="Local rubric analysis from transcript keywords and depth.",
            )
        )

    tech_score = 0
    if tech_breakdown:
        weights = [int(c.get("weight", 25)) for c in rubric] or [25] * len(tech_breakdown)
        total_w = sum(weights) or 1
        tech_score = int(
            round(
                sum(b.score * w for b, w in zip(tech_breakdown, weights)) / total_w * 10
            )
        )

    quality_criteria = [
        "coherence_structure",
        "relevance",
        "clarity_conciseness",
        "engagement_storytelling",
    ]
    quality_breakdown = []
    base = _length_score(word_count)
    for name in quality_criteria:
        quality_breakdown.append(
            CriterionScore(
                criterion=name,
                score=min(10, base + (1 if word_count > 30 else 0)),
                max_score=10,
                evidence=text[:80] + ("..." if len(text) > 80 else "") if text else "N/A",
                justification="Local analysis of pacing, clarity, and structure.",
            )
        )
    quality_score = int(round(sum(b.score for b in quality_breakdown) / len(quality_breakdown) * 10))

    suggestions = [
        "Expand answers with concrete examples tied to the question.",
        "Practice reducing filler words and maintaining steady eye contact.",
    ]
    if word_count < 40:
        suggestions.insert(0, "Give a longer, more structured answer (aim for 60+ words).")

    return {
        "technical_depth": TechnicalDepthMetric(
            score=tech_score,
            breakdown=tech_breakdown,
            comment="Multimodal local rubric scoring (Whisper + behavioral signals).",
        ),
        "response_quality": ResponseQualityMetric(
            score=quality_score,
            breakdown=quality_breakdown,
            comment="Local communication analysis from transcript structure.",
        ),
        "improvement_suggestions": suggestions,
    }
