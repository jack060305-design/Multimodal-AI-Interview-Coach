import logging
from typing import Any

from langchain_community.embeddings import HuggingFaceEmbeddings

from config import get_settings
from utils.device import get_accelerator_profile, get_embedding_model_kwargs

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def create_embeddings(model_name: str = DEFAULT_EMBEDDING_MODEL) -> Any:
    settings = get_settings()
    backend = settings.resolved_embedding_backend

    if backend == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.openai_embedding_model)

    profile = get_accelerator_profile()
    kwargs: dict[str, Any] = {"model_name": model_name}
    kwargs.update(get_embedding_model_kwargs())

    try:
        return HuggingFaceEmbeddings(**kwargs)
    except Exception as exc:
        device = kwargs.get("model_kwargs", {}).get("device")
        if device not in ("cpu", None):
            logger.warning("Embeddings on %s failed (%s) — falling back to CPU", device, exc)
            return HuggingFaceEmbeddings(model_name=model_name, model_kwargs={"device": "cpu"})
        raise
