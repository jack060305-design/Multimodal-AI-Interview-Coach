import os

from rubric_engine.vector_store import RubricVectorStore


def get_vector_store() -> RubricVectorStore:
    backend = os.getenv("VECTOR_STORE", "chroma").lower()
    if backend == "pinecone":
        from rubric_engine.pinecone_store import PineconeRubricStore

        return PineconeRubricStore()
    return RubricVectorStore()
