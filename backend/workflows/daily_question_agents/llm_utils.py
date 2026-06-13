"""LLM helpers for daily question agents."""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def call_llm_json(system: str, user: str) -> dict:
    from rubric_engine.evaluator import RubricEvaluator

    raw = RubricEvaluator()._call_llm(system, user)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("LLM returned non-JSON, attempting extraction: %s", exc)
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def append_trace(state: dict, node: str, decision: str) -> None:
    trace = list(state.get("agent_trace", []))
    trace.append({"node": node, "decision": decision})
    state["agent_trace"] = trace
