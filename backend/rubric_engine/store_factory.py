import os

from rubric_engine.vector_store import RubricVectorStore


def get_vector_store():
    from config import get_settings

    backend = get_settings().resolved_vector_store
    if backend == "pinecone":
        from rubric_engine.pinecone_store import PineconeRubricStore

        return PineconeRubricStore()
    if backend == "memory":
        from rubric_engine.memory_store import MemoryRubricStore

        return MemoryRubricStore()
    return RubricVectorStore()
