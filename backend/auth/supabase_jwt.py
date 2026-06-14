"""Verify Supabase Auth JWT (JWKS ES256, legacy HS256, or Auth API fallback)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from jose import JWTError, jwk, jwt
from jose.exceptions import JWKError

from config import get_settings

_jwks_cache: dict[str, Any] | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 3600


def _jwks_url() -> str | None:
    settings = get_settings()
    base = settings.supabase_url.rstrip("/")
    if not base:
        return None
    return f"{base}/auth/v1/.well-known/jwks.json"


def _load_jwks() -> dict[str, Any] | None:
    global _jwks_cache, _jwks_fetched_at

    url = _jwks_url()
    if not url:
        return None

    now = time.time()
    if _jwks_cache and now - _jwks_fetched_at < _JWKS_TTL_SECONDS:
        return _jwks_cache

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            _jwks_cache = json.loads(resp.read().decode())
            _jwks_fetched_at = now
            return _jwks_cache
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return _jwks_cache


def _decode_with_jwks(token: str) -> dict[str, Any] | None:
    jwks = _load_jwks()
    if not jwks or not jwks.get("keys"):
        return None

    settings = get_settings()
    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1" if settings.supabase_url else None

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg")
        keys = jwks["keys"]
        key_data = next((k for k in keys if k.get("kid") == kid), None)
        if key_data is None and len(keys) == 1:
            key_data = keys[0]
        if not key_data:
            return None

        public_key = jwk.construct(key_data)
        algorithms = [alg] if alg else ["ES256", "RS256"]
        issuers = [issuer] if issuer else [None]
        issuers.append(None) if issuer else None
        for iss in issuers:
            try:
                decode_kwargs: dict[str, Any] = {
                    "algorithms": algorithms,
                    "audience": "authenticated",
                }
                if iss:
                    decode_kwargs["issuer"] = iss
                return jwt.decode(token, public_key, **decode_kwargs)
            except JWTError:
                continue
        return None
    except (JWTError, JWKError, ValueError):
        return None


def _decode_with_secret(token: str) -> dict[str, Any] | None:
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


def _verify_via_auth_api(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    base = settings.supabase_url.rstrip("/")
    api_key = settings.supabase_anon_key
    if not base or not api_key:
        return None

    req = urllib.request.Request(
        f"{base}/auth/v1/user",
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return None
            user = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None

    user_id = user.get("id")
    if not user_id:
        return None

    return {
        "sub": user_id,
        "email": user.get("email"),
        "user_metadata": user.get("user_metadata") or {},
        "app_metadata": user.get("app_metadata") or {},
    }


def decode_supabase_token(token: str) -> dict[str, Any] | None:
    claims = _decode_with_jwks(token)
    if claims:
        return claims
    claims = _decode_with_secret(token)
    if claims:
        return claims
    return _verify_via_auth_api(token)
