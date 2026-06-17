"""Tests for Facebook Backend OAuth (Meta Graph API)."""

from __future__ import annotations

import importlib
import os
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def _load_facebook_oauth():
    import importlib.util

    spec = importlib.util.spec_from_file_location("facebook_oauth_test", BACKEND / "auth" / "facebook_oauth.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["config"] = importlib.import_module("config")
    spec.loader.exec_module(mod)
    return mod


def test_facebook_login_url_contains_required_params():
    fb = _load_facebook_oauth()
    os.environ["FACEBOOK_APP_ID"] = "test-app-id"
    os.environ["FACEBOOK_APP_SECRET"] = "test-secret"
    os.environ["FACEBOOK_REDIRECT_URI"] = "http://localhost:8000/auth/facebook/callback"
    import config

    config.get_settings.cache_clear()

    url = fb.facebook_login_url(state="csrf-state-xyz")
    assert "client_id=test-app-id" in url
    assert "redirect_uri=" in url
    assert "state=csrf-state-xyz" in url
    assert "scope=email%2Cpublic_profile" in url
    assert url.startswith("https://www.facebook.com/")

    os.environ.pop("FACEBOOK_APP_ID", None)
    os.environ.pop("FACEBOOK_APP_SECRET", None)
    os.environ.pop("FACEBOOK_REDIRECT_URI", None)
    config.get_settings.cache_clear()


def test_exchange_code_for_token_returns_access_token():
    fb = _load_facebook_oauth()
    os.environ["FACEBOOK_APP_ID"] = "app"
    os.environ["FACEBOOK_APP_SECRET"] = "secret"
    os.environ["FACEBOOK_REDIRECT_URI"] = "http://localhost:8000/auth/facebook/callback"
    import config

    config.get_settings.cache_clear()

    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"access_token":"fb-token-abc"}'
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        token = fb.exchange_code_for_token("auth-code")
    assert token == "fb-token-abc"

    os.environ.pop("FACEBOOK_APP_ID", None)
    os.environ.pop("FACEBOOK_APP_SECRET", None)
    os.environ.pop("FACEBOOK_REDIRECT_URI", None)
    config.get_settings.cache_clear()


def test_graph_http_error_raises_facebook_oauth_error():
    fb = _load_facebook_oauth()
    body = b'{"error":{"message":"Invalid OAuth access token."}}'
    err = urllib.error.HTTPError("http://x", 400, "Bad", {}, None)
    err.read = MagicMock(return_value=body)

    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(fb.FacebookOAuthError, match="Invalid OAuth access token"):
            fb.fetch_facebook_profile("bad-token")
