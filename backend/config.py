import os
from functools import lru_cache
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv(override=True)

DEFAULT_SUPABASE_PROJECT = "ttgdcomdfqmbqqiywoxw"


def _resolve_database_url() -> str:
    password = os.getenv("SUPABASE_DB_PASSWORD", "").strip()
    project = os.getenv("SUPABASE_PROJECT_REF", DEFAULT_SUPABASE_PROJECT).strip()

    if password:
        return (
            f"postgresql+psycopg2://postgres:{quote_plus(password)}"
            f"@db.{project}.supabase.co:5432/postgres?sslmode=require"
        )

    url = os.getenv("DATABASE_URL", "").strip()
    if url and "[YOUR-PASSWORD]" not in url:
        return url

    if os.getenv("DEPLOY_PROFILE", "local").lower() == "local":
        data_dir = os.getenv("DATA_DIR", "./data")
        db_path = os.path.join(data_dir, "app.db").replace("\\", "/")
        return f"sqlite:///{db_path}"

    return "postgresql+psycopg2://interview:interview@localhost:5432/interview_coach"


def _resolve_db_enabled() -> bool:
    if os.getenv("SUPABASE_DB_PASSWORD", "").strip():
        return True

    explicit = os.getenv("DB_ENABLED", "").strip().lower()
    if explicit == "true":
        return True
    if explicit == "false":
        return False

    return os.getenv("DEPLOY_PROFILE", "local").lower() == "local"


class Settings:
    def __init__(self) -> None:
        self.deploy_profile: str = os.getenv("DEPLOY_PROFILE", "local").lower()
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
        self.llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.whisper_backend: str = os.getenv("WHISPER_BACKEND", "").lower()
        self.vector_store: str = os.getenv("VECTOR_STORE", "chroma").lower()
        self.chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
        self.pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
        self.pinecone_index: str = os.getenv("PINECONE_INDEX", "interview-rubrics")
        self.pinecone_namespace: str = os.getenv("PINECONE_NAMESPACE", "rubrics")

        self.database_url: str = _resolve_database_url()
        self.db_enabled: bool = _resolve_db_enabled()

        self.storage_backend: str = os.getenv("STORAGE_BACKEND", "local").lower()
        self.aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.aws_region: str = os.getenv("AWS_REGION", "us-east-1")
        self.s3_bucket: str = os.getenv("S3_BUCKET", "interview-coach-videos")
        self.s3_endpoint_url: str = os.getenv("S3_ENDPOINT_URL", "")
        self.local_storage_dir: str = os.getenv("LOCAL_STORAGE_DIR", "./data/uploads")
        self.skip_video_storage: bool = os.getenv("SKIP_VIDEO_STORAGE", "false").lower() == "true"
        self.data_dir: str = os.getenv("DATA_DIR", "./data")
        self.work_dir: str = os.getenv("WORK_DIR", "./data/work")
        self.whisper_model: str = os.getenv("WHISPER_MODEL", "base")
        self.accelerator_mode: str = os.getenv("ACCELERATOR_MODE", "auto")

        self.langsmith_enabled: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
        self.langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "interview-coach")

        self.cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        self.frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

        self.jwt_secret: str = os.getenv("JWT_SECRET", os.getenv("AUTH_SECRET", "change-me-in-production"))
        self.jwt_expire_hours: int = int(os.getenv("JWT_EXPIRE_HOURS", "168"))
        self.facebook_app_id: str = os.getenv("FACEBOOK_APP_ID", "")
        self.facebook_app_secret: str = os.getenv("FACEBOOK_APP_SECRET", "")

        self.supabase_url: str = os.getenv("SUPABASE_URL", "")
        self.supabase_jwt_secret: str = os.getenv("SUPABASE_JWT_SECRET", "")
        self.supabase_anon_key: str = os.getenv(
            "SUPABASE_ANON_KEY",
            os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
        )

        self.firebase_project_id: str = os.getenv(
            "FIREBASE_PROJECT_ID",
            os.getenv("NEXT_PUBLIC_FIREBASE_PROJECT_ID", ""),
        ).strip()

        self.embedding_backend: str = os.getenv("EMBEDDING_BACKEND", "").lower()
        self.openai_embedding_model: str = os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )

        self.daily_questions_enabled: bool = (
            os.getenv("DAILY_QUESTIONS_ENABLED", "true").lower() == "true"
        )
        self.daily_questions_cron: str = os.getenv("DAILY_QUESTIONS_CRON", "0 6 * * *")
        self.daily_questions_per_role: int = int(os.getenv("DAILY_QUESTIONS_PER_ROLE", "3"))
        self.daily_questions_mode: str = os.getenv("DAILY_QUESTIONS_MODE", "agentic").lower()
        self.daily_questions_max_revisions: int = int(
            os.getenv("DAILY_QUESTIONS_MAX_REVISIONS", "1")
        )

    @property
    def is_cloud(self) -> bool:
        return self.deploy_profile == "cloud"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite:")

    @property
    def resolved_whisper_backend(self) -> str:
        if self.whisper_backend:
            return self.whisper_backend
        return "openai" if self.is_cloud else "local"

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url or self.supabase_jwt_secret or self.supabase_anon_key)

    @property
    def firebase_enabled(self) -> bool:
        return bool(self.firebase_project_id)

    @property
    def facebook_redirect_uri(self) -> str:
        base = os.getenv("FACEBOOK_REDIRECT_URI", "").strip()
        if base:
            return base
        api = os.getenv("PUBLIC_API_URL", "").strip().rstrip("/")
        if api:
            return f"{api}/auth/facebook/callback"
        return "http://localhost:8000/auth/facebook/callback"

    @property
    def resolved_embedding_backend(self) -> str:
        if self.embedding_backend:
            return self.embedding_backend
        return "openai" if self.is_cloud else "huggingface"

    @property
    def resolved_vector_store(self) -> str:
        if self.is_cloud and self.vector_store == "chroma":
            if self.resolved_embedding_backend == "openai":
                return "chroma"
            return "memory"
        return self.vector_store


@lru_cache
def get_settings() -> Settings:
    return Settings()
