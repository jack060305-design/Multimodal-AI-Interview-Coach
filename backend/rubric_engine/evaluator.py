import json
import os
import re
from typing import Any

from config import get_settings
from schemas import (
    CriterionScore,
    ResponseQualityMetric,
    Role,
    TechnicalDepthMetric,
    TranscriptResult,
)
from tracing.langsmith_setup import configure_langsmith

EVALUATOR_SYSTEM = """You are a strict technical interviewer for {role}.
Evaluate the candidate's answer STRICTLY based on the provided rubric only.
Do not invent new criteria. Do not score outside the rubric levels.
Every score must cite evidence quoted from the transcript.
If the transcript lacks evidence for a criterion, score it at the lowest level."""

EVALUATOR_USER = """Rubric (JSON):
{rubric_json}

Ideal Answer:
{ideal_answer}

Evaluation Guidelines:
{guidelines}

Candidate Transcript:
{transcript}

For each criterion in the rubric:
- Give score using the rubric level keys (0, 5, 8, 10 or as defined)
- Short evidence quote from transcript (or "N/A" if missing)
- Brief justification tied only to rubric levels

Also evaluate response_quality using these fixed criteria (each 0-10):
1. coherence_structure
2. relevance
3. clarity_conciseness
4. engagement_storytelling

Output ONLY valid JSON in this exact format:
{{
  "technical_depth": {{
    "score": <0-100 weighted from rubric>,
    "breakdown": [
      {{"criterion": "...", "score": <int>, "max_score": 10, "evidence": "...", "justification": "..."}}
    ],
    "comment": "..."
  }},
  "response_quality": {{
    "score": <0-100>,
    "breakdown": [
      {{"criterion": "coherence_structure", "score": <int>, "max_score": 10, "evidence": "...", "justification": "..."}}
    ],
    "comment": "..."
  }},
  "improvement_suggestions": ["...", "..."]
}}"""


class RubricEvaluator:
    def __init__(self, model: str | None = None, provider: str | None = None):
        settings = get_settings()
        self.model = model or settings.llm_model
        self.provider = (provider or settings.llm_provider).lower()
        configure_langsmith()

    def _call_llm(self, system: str, user: str) -> str:
        if self.provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content or "{}"

        if self.provider == "anthropic":
            import anthropic

            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            resp = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user + "\n\nRespond with JSON only."}],
                temperature=0.1,
            )
            return resp.content[0].text

        if self.provider == "gemini":
            from google import genai

            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            resp = client.models.generate_content(
                model=self.model,
                contents=f"{system}\n\n{user}\n\nRespond with JSON only.",
                config={"response_mime_type": "application/json", "temperature": 0.1},
            )
            return resp.text or "{}"

        raise ValueError(
            f"Unsupported LLM provider: {self.provider}. "
            "Use openai, anthropic, or gemini."
        )

    def evaluate(
        self,
        role: Role,
        transcript: TranscriptResult,
        rubric_payload: dict[str, Any],
    ) -> dict[str, Any]:
        system = EVALUATOR_SYSTEM.format(role=role.value.replace("_", " ").title())
        user = EVALUATOR_USER.format(
            rubric_json=json.dumps(rubric_payload["rubric"], indent=2, ensure_ascii=False),
            ideal_answer=rubric_payload["ideal_answer"],
            guidelines=rubric_payload.get("evaluation_guidelines", ""),
            transcript=transcript.text,
        )

        raw = self._call_llm(system, user)
        parsed = self._parse_json(raw)

        tech = self._to_technical_metric(parsed.get("technical_depth", {}))
        quality = self._to_quality_metric(parsed.get("response_quality", {}))

        return {
            "technical_depth": tech,
            "response_quality": quality,
            "improvement_suggestions": parsed.get("improvement_suggestions", []),
        }

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise

    def _to_breakdown(self, items: list[dict]) -> list[CriterionScore]:
        return [
            CriterionScore(
                criterion=item.get("criterion", ""),
                score=int(item.get("score", 0)),
                max_score=int(item.get("max_score", 10)),
                evidence=item.get("evidence", ""),
                justification=item.get("justification", ""),
            )
            for item in items
        ]

    def _to_technical_metric(self, data: dict) -> TechnicalDepthMetric:
        return TechnicalDepthMetric(
            score=int(data.get("score", 0)),
            breakdown=self._to_breakdown(data.get("breakdown", [])),
            comment=data.get("comment", ""),
        )

    def _to_quality_metric(self, data: dict) -> ResponseQualityMetric:
        return ResponseQualityMetric(
            score=int(data.get("score", 0)),
            breakdown=self._to_breakdown(data.get("breakdown", [])),
            comment=data.get("comment", ""),
        )
