"""Facebook Login OAuth2 (authorization code flow)."""

from __future__ import annotations

import urllib.parse
import urllib.request
import json

from config import get_settings

GRAPH = "https://graph.facebook.com/v19.0"


def facebook_login_url(*, state: str) -> str:
    settings = get_settings()
    if not settings.facebook_app_id:
        raise ValueError("FACEBOOK_APP_ID not configured")
    params = urllib.parse.urlencode(
        {
            "client_id": settings.facebook_app_id,
            "redirect_uri": settings.facebook_redirect_uri,
            "state": state,
            "scope": "email,public_profile",
            "response_type": "code",
        }
    )
    return f"https://www.facebook.com/v19.0/dialog/oauth?{params}"


def exchange_code_for_token(code: str) -> str:
    settings = get_settings()
    params = urllib.parse.urlencode(
        {
            "client_id": settings.facebook_app_id,
            "client_secret": settings.facebook_app_secret,
            "redirect_uri": settings.facebook_redirect_uri,
            "code": code,
        }
    )
    url = f"{GRAPH}/oauth/access_token?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    token = data.get("access_token")
    if not token:
        raise ValueError(data.get("error", {}).get("message", "Facebook token exchange failed"))
    return token


def fetch_facebook_profile(access_token: str) -> dict:
    params = urllib.parse.urlencode(
        {"fields": "id,name,email,picture.type(large)", "access_token": access_token}
    )
    url = f"{GRAPH}/me?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())
