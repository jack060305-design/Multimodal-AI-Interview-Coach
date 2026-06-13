import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # local = full multimodal stack; cloud = API Whisper + transcript metrics (Render/Railway)
    deploy_profile: str = os.getenv("DEPLOY_PROFILE", "local").lower()

    # LLM
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Whisper: local (faster-whisper) | openai (Whisper API — required for cloud)
    whisper_backend: str = os.getenv("WHISPER_BACKEND", "").lower()

    # Vector store: chroma | pinecone | memory
    vector_store: str = os.getenv("VECTOR_STORE", "chroma").lower()
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index: str = os.getenv("PINECONE_INDEX", "interview-rubrics")
    pinecone_namespace: str = os.getenv("PINECONE_NAMESPACE", "rubrics")

    # Postgres
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://interview:interview@localhost:5432/interview_coach",
    )
    db_enabled: bool = os.getenv("DB_ENABLED", "true").lower() == "true"

    # S3 / object storage
    storage_backend: str = os.getenv("STORAGE_BACKEND", "local").lower()
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket: str = os.getenv("S3_BUCKET", "interview-coach-videos")
    s3_endpoint_url: str = os.getenv("S3_ENDPOINT_URL", "")
    local_storage_dir: str = os.getenv("LOCAL_STORAGE_DIR", "./data/uploads")

    # Processing (device resolved at runtime via utils.device — see ACCELERATOR_MODE)
    work_dir: str = os.getenv("WORK_DIR", "./data/work")
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    accelerator_mode: str = os.getenv("ACCELERATOR_MODE", "auto")

    # LangSmith
    langsmith_enabled: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "interview-coach")

    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

    # Daily LLM question generation (Scheduled Job + LLM)
    daily_questions_enabled: bool = (
        os.getenv("DAILY_QUESTIONS_ENABLED", "true").lower() == "true"
    )
    daily_questions_cron: str = os.getenv("DAILY_QUESTIONS_CRON", "0 6 * * *")
    daily_questions_per_role: int = int(os.getenv("DAILY_QUESTIONS_PER_ROLE", "3"))
    # agentic = LangGraph Planner/Researcher/Generator/Critic; simple = one-shot LLM per role
    daily_questions_mode: str = os.getenv("DAILY_QUESTIONS_MODE", "agentic").lower()
    daily_questions_max_revisions: int = int(os.getenv("DAILY_QUESTIONS_MAX_REVISIONS", "1"))

    @property
    def is_cloud(self) -> bool:
        return self.deploy_profile == "cloud"

    @property
    def resolved_whisper_backend(self) -> str:
        if self.whisper_backend:
            return self.whisper_backend
        return "openai" if self.is_cloud else "local"

    @property
    def resolved_vector_store(self) -> str:
        if self.is_cloud and self.vector_store == "chroma":
            return "memory"
        return self.vector_store


@lru_cache
def get_settings() -> Settings:
    return Settings()
