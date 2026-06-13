from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from auth.jwt_tokens import decode_access_token
from db.database import db_session
from db.models import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session | None = Depends(db_session),
) -> User | None:
    if db is None or creds is None or not creds.credentials:
        return None
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()


def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    if user is None:
        raise HTTPException(401, "Authentication required")
    return user


def get_current_user_id_optional(
    user: User | None = Depends(get_current_user_optional),
) -> UUID | None:
    return user.id if user else None
