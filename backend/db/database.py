import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings
from db.models import Base

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def init_db() -> bool:
    global _engine, _SessionLocal
    settings = get_settings()
    if not settings.db_enabled:
        logger.info("Postgres disabled (DB_ENABLED=false)")
        return False

    try:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
        Base.metadata.create_all(bind=_engine)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        logger.info("Postgres connected and tables ready")
        return True
    except Exception as exc:
        logger.warning("Postgres unavailable, running without persistence: %s", exc)
        _engine = None
        _SessionLocal = None
        return False


def get_db() -> Session | None:
    if _SessionLocal is None:
        return None
    return _SessionLocal()
