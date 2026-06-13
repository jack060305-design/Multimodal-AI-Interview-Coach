from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt

from config import get_settings

ALGORITHM = "HS256"


def create_access_token(user_id: UUID, *, expires_hours: int | None = None) -> str:
    settings = get_settings()
    hours = expires_hours if expires_hours is not None else settings.jwt_expire_hours
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> UUID | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return UUID(sub) if sub else None
    except (JWTError, ValueError):
        return None
