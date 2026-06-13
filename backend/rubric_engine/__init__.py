from .evaluator import RubricEvaluator
from .store_factory import get_vector_store

__all__ = ["RubricEvaluator", "get_vector_store"]


def __getattr__(name: str):
    if name == "RubricVectorStore":
        from .vector_store import RubricVectorStore

        return RubricVectorStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
