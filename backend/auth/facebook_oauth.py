"""Facebook Login OAuth2 (authorization code flow) via Meta Graph API."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from config import get_settings

GRAPH_VERSION = "v21.0"
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
OAUTH_DIALOG = f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"
DEFAULT_SCOPES = "email,public_profile"


class FacebookOAuthError(Exception):
    """Raised when Meta OAuth or Graph API returns an error."""


def _read_json_response(resp: urllib.response.addinfourl) -> dict:
    try:
        return json.loads(resp.read().decode())
    except json.JSONDecodeError as exc:
        raise FacebookOAuthError("Invalid response from Facebook API") from exc


def _graph_error_message(data: dict) -> str:
    err = data.get("error") or {}
    if isinstance(err, dict):
        return str(err.get("message") or err.get("type") or "Facebook API error")
    return str(data)


def _request_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return _read_json_response(resp)
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode())
            raise FacebookOAuthError(_graph_error_message(body)) from exc
        except json.JSONDecodeError:
            raise FacebookOAuthError(f"Facebook HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise FacebookOAuthError("Could not reach Facebook — check your network") from exc


def facebook_login_url(*, state: str) -> str:
    settings = get_settings()
    if not settings.facebook_app_id:
        raise ValueError("FACEBOOK_APP_ID not configured")
    params = urllib.parse.urlencode(
        {
            "client_id": settings.facebook_app_id,
            "redirect_uri": settings.facebook_redirect_uri,
            "state": state,
            "scope": DEFAULT_SCOPES,
            "response_type": "code",
        }
    )
    return f"{OAUTH_DIALOG}?{params}"


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
    data = _request_json(f"{GRAPH}/oauth/access_token?{params}")
    token = data.get("access_token")
    if not token:
        raise FacebookOAuthError(_graph_error_message(data))
    return str(token)


def fetch_facebook_profile(access_token: str) -> dict:
    params = urllib.parse.urlencode(
        {"fields": "id,name,email,picture.type(large)", "access_token": access_token}
    )
    return _request_json(f"{GRAPH}/me?{params}")
