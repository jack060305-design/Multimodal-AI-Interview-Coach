import logging
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from auth.jwt_tokens import decode_access_token
from auth.repository import UserRepository
from auth.supabase_jwt import decode_supabase_token
from db.database import db_session, is_db_connected
from db.models import User

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


def _user_from_supabase_claims(db: Session, claims: dict) -> User | None:
    sub = claims.get("sub")
    if not sub:
        return None
    try:
        user_id = UUID(sub)
    except ValueError:
        return None
    meta = claims.get("user_metadata") or {}
    email = claims.get("email")
    name = (
        meta.get("full_name")
        or meta.get("name")
        or (email.split("@")[0] if email else "User")
    )
    avatar = meta.get("avatar_url") or meta.get("picture")
    try:
        return UserRepository(db).upsert_supabase_user(
            user_id=user_id,
            email=email,
            name=str(name),
            avatar_url=avatar,
        )
    except SQLAlchemyError as exc:
        logger.exception("Failed to sync Supabase user %s into Postgres", user_id)
        raise HTTPException(
            503,
            "Database sync failed — check DATABASE_URL and users table on the API server.",
        ) from exc


def _token_is_valid(token: str) -> bool:
    if decode_supabase_token(token):
        return True
    return decode_access_token(token) is not None


def _database_unavailable() -> HTTPException:
    if not is_db_connected():
        return HTTPException(
            503,
            "Database not connected — set DB_ENABLED=true and a valid DATABASE_URL, then redeploy.",
        )
    return HTTPException(503, "Database not available")


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session | None = Depends(db_session),
) -> User | None:
    if creds is None or not creds.credentials:
        return None
    if db is None:
        return None

    token = creds.credentials
    claims = decode_supabase_token(token)
    if claims:
        return _user_from_supabase_claims(db, claims)

    user_id = decode_access_token(token)
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session | None = Depends(db_session),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(401, "Authentication required")

    token = creds.credentials
    if not _token_is_valid(token):
        raise HTTPException(
            401,
            "Invalid or expired session — sign out and sign in again.",
        )

    if db is None:
        raise _database_unavailable()

    user = get_current_user_optional(creds=creds, db=db)
    if user is None:
        raise HTTPException(401, "Authentication required")
    return user


def get_current_user_id_optional(
    user: User | None = Depends(get_current_user_optional),
) -> UUID | None:
    return user.id if user else None
