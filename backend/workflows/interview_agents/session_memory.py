"""Session-scoped recall for Followup agent (Friday-style RAG over prior turns)."""

from __future__ import annotations

from typing import Any


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embed_turn_text(text: str) -> list[float]:
    try:
        from rubric_engine.embeddings import create_embeddings

        emb = create_embeddings()
        return emb.embed_query(text[:2000])
    except Exception:
        return []


def record_turn_embedding(
    turns: list[dict[str, Any]],
    *,
    question: str,
    answer: str,
    competency: str,
    score: int,
) -> list[dict[str, Any]]:
    updated = list(turns)
    updated.append(
        {
            "question": question,
            "answer": answer,
            "competency": competency,
            "score": score,
            "embedding": embed_turn_text(f"{question}\n{answer}"),
        }
    )
    return updated


def find_recurring_gaps(
    turns: list[dict[str, Any]],
    competency: str,
    min_score: int = 3,
) -> bool:
    weak = [t for t in turns if t.get("competency") == competency and t.get("score", 5) < min_score]
    if len(weak) >= 2:
        return True

    if len(turns) < 2:
        return False

    current = turns[-1].get("embedding") or []
    if not current:
        return len(weak) >= 1

    for prior in turns[:-1]:
        if prior.get("competency") != competency:
            continue
        if prior.get("score", 5) >= min_score:
            continue
        prior_emb = prior.get("embedding") or []
        if prior_emb and _cosine(current, prior_emb) > 0.75:
            return True

    return False
