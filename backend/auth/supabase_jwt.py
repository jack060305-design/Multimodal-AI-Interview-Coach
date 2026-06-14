"""Verify Supabase Auth JWT (HS256, audience authenticated)."""

from __future__ import annotations

from typing import Any

from jose import JWTError, jwt

from config import get_settings


def decode_supabase_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    secret = settings.supabase_jwt_secret
    if not secret:
        return None
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
        return None
