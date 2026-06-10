import json
import os
from typing import Any

from langchain_community.vectorstores import Pinecone as PineconeVS
from pinecone import Pinecone, ServerlessSpec

from rubric_engine.embeddings import create_embeddings
from schemas import Role, RubricDocument
from rubric_engine.vector_store import rubric_doc_text


class PineconeRubricStore:
    def __init__(self):
        api_key = os.getenv("PINECONE_API_KEY", "")
        if not api_key:
            raise ValueError("PINECONE_API_KEY required when VECTOR_STORE=pinecone")

        self.index_name = os.getenv("PINECONE_INDEX", "interview-rubrics")
        self.namespace = os.getenv("PINECONE_NAMESPACE", "rubrics")
        self.embeddings = create_embeddings()
        self.pc = Pinecone(api_key=api_key)
        self._ensure_index()
        self._store: PineconeVS | None = None

    def _ensure_index(self) -> None:
        names = {idx.name for idx in self.pc.list_indexes()}
        if self.index_name not in names:
            self.pc.create_index(
                name=self.index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

    @property
    def store(self) -> PineconeVS:
        if self._store is None:
            index = self.pc.Index(self.index_name)
            self._store = PineconeVS(
                index=index,
                embedding=self.embeddings,
                text_key="text",
                namespace=self.namespace,
            )
        return self._store

    def _meta_to_payload(self, meta: dict[str, Any]) -> dict:
        return {
            "role": meta["role"],
            "question": meta["question"],
            "question_id": meta["question_id"],
            "rubric": json.loads(meta["rubric_json"]),
            "ideal_answer": meta["ideal_answer"],
            "evaluation_guidelines": meta.get("evaluation_guidelines", ""),
            "total_points": meta.get("total_points", 100),
        }

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

    def retrieve(self, role: Role, question: str, k: int = 3) -> list[dict]:
        query = f"Role: {role.value}\nQuestion: {question}"
        docs = self.store.similarity_search_with_score(query, k=k)

        results = []
        for doc, score in docs:
            meta = doc.metadata
            if meta.get("role") != role.value:
                continue
            payload = self._meta_to_payload(meta)
            payload["similarity_score"] = float(score)
            results.append(payload)

        if not results and docs:
            doc, score = docs[0]
            payload = self._meta_to_payload(doc.metadata)
            payload["similarity_score"] = float(score)
            results.append(payload)

        return results

    def get_by_question_id(self, role: Role, question_id: str) -> dict | None:
        doc_id = f"{role.value}:{question_id}"
        try:
            index = self.pc.Index(self.index_name)
            fetched = index.fetch(ids=[doc_id], namespace=self.namespace)
            vectors = fetched.vectors or {}
            if doc_id not in vectors:
                return None
            return self._meta_to_payload(vectors[doc_id].metadata or {})
        except Exception:
            return None
