"""In-memory rubric store for cloud deploy (no Chroma / sentence-transformers)."""

from __future__ import annotations

from rubrics.registry import rubric_doc_to_payload
from rubrics.sample_rubrics import SAMPLE_RUBRICS, RUBRIC_BY_ID
from schemas import Role, RubricDocument


class MemoryRubricStore:
    def __init__(self) -> None:
        self._payloads: dict[str, dict] = {}
        for doc in SAMPLE_RUBRICS:
            key = f"{doc.role.value}:{doc.question_id}"
            self._payloads[key] = rubric_doc_to_payload(doc)

    def ingest(self, rubrics: list[RubricDocument]) -> int:
        for doc in rubrics:
            key = f"{doc.role.value}:{doc.question_id}"
            self._payloads[key] = rubric_doc_to_payload(doc)
        return len(rubrics)

    def retrieve(self, role: Role, question: str, k: int = 3) -> list[dict]:
        matches = [
            p
            for p in self._payloads.values()
            if p["role"] == role.value
            and (p["question"] in question or question in p["question"])
        ]
        if not matches:
            matches = [p for p in self._payloads.values() if p["role"] == role.value]
        return matches[:k]

    def get_by_question_id(self, role: Role, question_id: str) -> dict | None:
        return self._payloads.get(f"{role.value}:{question_id}") or (
            rubric_doc_to_payload(doc)
            if (doc := RUBRIC_BY_ID.get(f"{role.value}:{question_id}"))
            else None
        )
