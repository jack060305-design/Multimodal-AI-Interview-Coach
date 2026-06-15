"""Verify Firebase Auth ID tokens (Google sign-in via Firebase)."""

from __future__ import annotations

from typing import Any

from config import get_settings


def decode_firebase_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    project_id = settings.firebase_project_id
    if not project_id:
        return None

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
    except ImportError:
        return None

    try:
        claims = id_token.verify_firebase_token(
            token,
            google_requests.Request(),
            audience=project_id,
        )
        return dict(claims)
    except (ValueError, OSError):
        return None


def firebase_uid_to_user_id(firebase_uid: str):
    import uuid

    return uuid.uuid5(uuid.NAMESPACE_URL, f"firebase:{firebase_uid}")
