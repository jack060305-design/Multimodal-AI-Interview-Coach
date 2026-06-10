import logging
import os

from config import get_settings

logger = logging.getLogger(__name__)


def configure_langsmith() -> bool:
    settings = get_settings()
    if not settings.langsmith_enabled:
        return False

    if not settings.langsmith_api_key:
        logger.warning("LANGCHAIN_TRACING_V2=true but LANGSMITH_API_KEY is missing")
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    logger.info("LangSmith tracing enabled for project=%s", settings.langsmith_project)
    return True
