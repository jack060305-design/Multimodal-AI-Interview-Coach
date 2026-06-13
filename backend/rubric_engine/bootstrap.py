"""Warm rubric vector index on startup (cloud Chroma + OpenAI embeddings)."""

from __future__ import annotations

import logging

from config import get_settings

logger = logging.getLogger(__name__)


def bootstrap_vector_index() -> None:
    settings = get_settings()
    backend = settings.resolved_vector_store
    if backend not in ("chroma", "pinecone"):
        return
    try:
        from rubric_engine.store_factory import get_vector_store
        from rubrics.sample_rubrics import SAMPLE_RUBRICS

        store = get_vector_store()
        count = store.ingest(SAMPLE_RUBRICS)
        logger.info("Vector index ready (%s): %s rubrics", backend, count)
    except Exception as exc:
        logger.warning("Vector index bootstrap failed: %s", exc)
