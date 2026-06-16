import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from config import get_settings
from db.models import Base

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None
_db_init_error: str | None = None


def _normalize_database_url(url: str) -> str:
    if url.startswith("sqlite:"):
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _connect_args(url: str) -> dict:
    if "supabase.co" in url and "sslmode=" not in url:
        return {"sslmode": "require"}
    return {}


def _uses_transaction_pooler(url: str) -> bool:
    """Supavisor transaction mode (port 6543) does not support prepared statements."""
    return ":6543/" in url or ":6543?" in url or "pgbouncer=true" in url.lower()


def _engine_kwargs(url: str, connect_args: dict) -> dict:
    kwargs: dict = {
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }
    if _uses_transaction_pooler(url):
        kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = 3
        kwargs["max_overflow"] = 2
    return kwargs


def _migrate_schema(engine) -> None:
    from sqlalchemy import inspect

    insp = inspect(engine)
    if "evaluations" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("evaluations")}
    if "user_id" not in cols:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE evaluations ADD COLUMN user_id UUID "
                    "REFERENCES users(id) ON DELETE SET NULL"
                )
            )
        logger.info("Migrated evaluations.user_id column")


def init_db() -> bool:
    global _engine, _SessionLocal, _db_init_error
    settings = get_settings()
    if not settings.db_enabled:
        _db_init_error = None
        logger.info("Postgres disabled (DB_ENABLED=false)")
        return False

    try:
        url = _normalize_database_url(settings.database_url)
        if url.startswith("sqlite:"):
            db_file = url.replace("sqlite:///", "", 1)
            Path(db_file).parent.mkdir(parents=True, exist_ok=True)
            connect_args = {"check_same_thread": False}
        else:
            connect_args = _connect_args(url)
        _engine = create_engine(url, **_engine_kwargs(url, connect_args))
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=_engine)
        _migrate_schema(_engine)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        _db_init_error = None
        logger.info("Database connected and tables ready (%s)", url.split("://", 1)[0])
        return True
    except Exception as exc:
        _db_init_error = str(exc)
        logger.warning("Postgres unavailable, running without persistence: %s", exc)
        _engine = None
        _SessionLocal = None
        return False


def is_db_connected() -> bool:
    return _SessionLocal is not None


def db_status() -> dict:
    settings = get_settings()
    return {
        "configured": settings.db_enabled,
        "connected": is_db_connected(),
        "error": _db_init_error,
    }


def get_db() -> Session | None:
    if _SessionLocal is None:
        return None
    return _SessionLocal()


def db_session():
    """FastAPI dependency — yields a DB session or None when disabled."""
    db = get_db()
    if db is None:
        yield None
        return
    try:
        yield db
    finally:
        db.close()
