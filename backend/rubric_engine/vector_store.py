import json
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma

from rubric_engine.embeddings import create_embeddings
from schemas import Role, RubricDocument


def rubric_doc_text(rubric: RubricDocument) -> str:
    criteria = "\n".join(
        f"- {c.criterion} (weight {c.weight})" for c in rubric.rubric
    )
    return (
        f"Role: {rubric.role.value}\n"
        f"Question: {rubric.question}\n"
        f"Question ID: {rubric.question_id}\n"
        f"Criteria:\n{criteria}\n"
        f"Ideal Answer:\n{rubric.ideal_answer}\n"
        f"Guidelines:\n{rubric.evaluation_guidelines}"
    )


class RubricVectorStore:
    def __init__(self, persist_dir: str | None = None):
        base = persist_dir or os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
        self.persist_dir = Path(base)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.embeddings = create_embeddings()
        self._store: Chroma | None = None

    @property
    def store(self) -> Chroma:
        if self._store is None:
            self._store = Chroma(
                collection_name="interview_rubrics",
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_dir),
                client_settings=Settings(anonymized_telemetry=False),
            )
        return self._store

    def ingest(self, rubrics: list[RubricDocument]) -> int:
        texts, metadatas, ids = [], [], []
        for r in rubrics:
            texts.append(rubric_doc_text(r))
            metadatas.append(
                {
                    "role": r.role.value,
                    "question": r.question,
                    "question_id": r.question_id,
                    "rubric_json": json.dumps(
                        [c.model_dump() for c in r.rubric], ensure_ascii=False
                    ),
                    "ideal_answer": r.ideal_answer,
                    "evaluation_guidelines": r.evaluation_guidelines,
                    "total_points": r.total_points,
                }
            )
            ids.append(f"{r.role.value}:{r.question_id}")

        self.store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        return len(rubrics)

    def retrieve(
        self, role: Role, question: str, k: int = 3
    ) -> list[dict]:
        query = f"Role: {role.value}\nQuestion: {question}"
        docs = self.store.similarity_search_with_score(query, k=k)

        results = []
        for doc, score in docs:
            meta = doc.metadata
            if meta.get("role") != role.value:
                continue
            results.append(
                {
                    "role": meta["role"],
                    "question": meta["question"],
                    "question_id": meta["question_id"],
                    "rubric": json.loads(meta["rubric_json"]),
                    "ideal_answer": meta["ideal_answer"],
                    "evaluation_guidelines": meta.get("evaluation_guidelines", ""),
                    "total_points": meta.get("total_points", 100),
                    "similarity_score": float(score),
                }
            )

        if not results and docs:
            doc, score = docs[0]
            meta = doc.metadata
            results.append(
                {
                    "role": meta["role"],
                    "question": meta["question"],
                    "question_id": meta["question_id"],
                    "rubric": json.loads(meta["rubric_json"]),
                    "ideal_answer": meta["ideal_answer"],
                    "evaluation_guidelines": meta.get("evaluation_guidelines", ""),
                    "total_points": meta.get("total_points", 100),
                    "similarity_score": float(score),
                }
            )

        return results

    def get_by_question_id(self, role: Role, question_id: str) -> dict | None:
        client = chromadb.PersistentClient(path=str(self.persist_dir))
        collection = client.get_or_create_collection("interview_rubrics")
        result = collection.get(ids=[f"{role.value}:{question_id}"])
        if not result["ids"]:
            return None
        meta = result["metadatas"][0]
        return {
            "role": meta["role"],
            "question": meta["question"],
            "question_id": meta["question_id"],
            "rubric": json.loads(meta["rubric_json"]),
            "ideal_answer": meta["ideal_answer"],
            "evaluation_guidelines": meta.get("evaluation_guidelines", ""),
            "total_points": meta.get("total_points", 100),
        }
