"""Smoke tests for login/database sync fixes."""

from __future__ import annotations

import importlib
import os
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DB_ENABLED", "false")
os.environ.setdefault("SUPABASE_URL", "https://ttgdcomdfqmbqqiywoxw.supabase.co")
os.environ.setdefault(
    "SUPABASE_ANON_KEY",
    "sb_publishable_oAWTc_IxskWk11vaU7JzOg_74RccE7t",
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


import importlib.util  # noqa: E402

from db.models import Base, User  # noqa: E402


def test_jwks_loads_from_supabase():
    jwt_mod = _load_module("supabase_jwt_test", BACKEND / "auth" / "supabase_jwt.py")
    jwks = jwt_mod._load_jwks()
    assert jwks is not None
    assert len(jwks.get("keys", [])) >= 1
    assert jwt_mod.decode_supabase_token("not-a-jwt") is None


def test_db_status_when_disabled():
    _reload_config()
    os.environ["DB_ENABLED"] = "false"
    os.environ["DEPLOY_PROFILE"] = "cloud"
    os.environ.pop("SUPABASE_DB_PASSWORD", None)
    import config
    config.get_settings.cache_clear()
    db_mod = _load_module("database_test", BACKEND / "db" / "database.py")
    db_mod.init_db()
    status = db_mod.db_status()
    assert status["configured"] is False
    assert status["connected"] is False


def _reload_config():
    import config

    importlib.reload(config)
    config.get_settings.cache_clear()
    return config


def test_local_sqlite_default_when_no_password():
    _reload_config()
    os.environ.pop("SUPABASE_DB_PASSWORD", None)
    os.environ["DEPLOY_PROFILE"] = "local"
    os.environ["DB_ENABLED"] = "true"
    os.environ.pop("DATABASE_URL", None)
    import config
    config.get_settings.cache_clear()
    s = config.get_settings()
    assert s.db_enabled is True
    assert s.database_url.startswith("sqlite:")
    assert s.is_sqlite is True


def test_supabase_url_when_password_set():
    _reload_config()
    os.environ["SUPABASE_DB_PASSWORD"] = "test-pass"
    os.environ["DEPLOY_PROFILE"] = "local"
    import config
    config.get_settings.cache_clear()
    s = config.get_settings()
    assert "postgresql" in s.database_url
    assert "test-pass" in s.database_url or "test%2Dpass" in s.database_url
    os.environ.pop("SUPABASE_DB_PASSWORD", None)


def test_db_status_tracks_connection_failure():
    _reload_config()
    os.environ["DB_ENABLED"] = "true"
    os.environ["DATABASE_URL"] = "postgresql://bad:bad@127.0.0.1:1/none"
    os.environ.pop("SUPABASE_DB_PASSWORD", None)
    import config
    config.get_settings.cache_clear()
    db_mod = _load_module("database_test2", BACKEND / "db" / "database.py")
    ok = db_mod.init_db()
    assert ok is False
    assert db_mod.is_db_connected() is False
    status = db_mod.db_status()
    assert status["configured"] is True
    assert status["connected"] is False
    assert status["error"]


def test_upsert_supabase_user_reconciles_email_conflict():
    _reload_config()
    passwords_mod = _load_module("passwords_test", BACKEND / "auth" / "passwords.py")
    sys.modules["auth.passwords"] = passwords_mod
    repo_mod = _load_module("repository_test", BACKEND / "auth" / "repository.py")
    UserRepository = repo_mod.UserRepository

    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(bind=engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE evaluations (id TEXT PRIMARY KEY, user_id TEXT)"
        )
    Session = sessionmaker(bind=engine)
    db = Session()

    legacy_id = uuid.uuid4()
    supabase_id = uuid.uuid4()
    db.add(
        User(
            id=legacy_id,
            email="tester@example.com",
            name="Legacy",
        )
    )
    db.commit()

    repo = UserRepository(db)
    user = repo.upsert_supabase_user(
        user_id=supabase_id,
        email="tester@example.com",
        name="Supabase User",
    )

    assert user.id == supabase_id
    assert user.email == "tester@example.com"
    assert db.query(User).filter(User.id == legacy_id).first() is None
    db.close()
