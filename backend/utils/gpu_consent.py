"""
GPU consent — user must allow GPU use (once / always / never).
Default: CPU until user consents (safe for all machines).
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

_request_consent: ContextVar[str | None] = ContextVar("gpu_consent_request", default=None)

CONSENT_CHOICES = frozenset({"once", "always", "never", "prompt"})


def _consent_file() -> Path:
    base = Path(os.getenv("GPU_CONSENT_FILE", "./data/gpu_consent.json"))
    base.parent.mkdir(parents=True, exist_ok=True)
    return base


def load_stored_consent() -> str | None:
    env = os.getenv("GPU_CONSENT", "").strip().lower()
    if env in ("always", "never"):
        return env

    path = _consent_file()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        choice = data.get("choice")
        if choice in ("always", "never"):
            return choice
    except Exception as exc:
        logger.warning("Could not read GPU consent file: %s", exc)
    return None


def save_stored_consent(choice: str) -> None:
    if choice not in ("always", "never"):
        return
    path = _consent_file()
    path.write_text(
        json.dumps({"choice": choice}, indent=2),
        encoding="utf-8",
    )
    logger.info("GPU consent saved: %s", choice)


def clear_stored_consent() -> None:
    path = _consent_file()
    if path.exists():
        path.unlink()


def get_request_consent() -> str | None:
    return _request_consent.get()


def resolve_consent(explicit: str | None = None) -> str:
    """
    Returns: once | always | never | unset
    unset = no permission yet → use CPU
    """
    raw = (explicit or get_request_consent() or "").strip().lower()
    if raw == "once":
        return "once"
    if raw == "always":
        save_stored_consent("always")
        return "always"
    if raw == "never":
        save_stored_consent("never")
        return "never"

    stored = load_stored_consent()
    if stored:
        return stored

    return "unset"


def is_gpu_allowed(explicit: str | None = None) -> bool:
    return resolve_consent(explicit) in ("once", "always")


def consent_status() -> dict:
    stored = load_stored_consent()
    resolved = resolve_consent()
    return {
        "stored_consent": stored,
        "resolved_consent": resolved,
        "gpu_allowed": resolved in ("once", "always"),
        "requires_prompt": resolved == "unset",
    }


@contextmanager
def gpu_consent_scope(consent: str | None) -> Iterator[None]:
    token = _request_consent.set(consent)
    try:
        yield
    finally:
        _request_consent.reset(token)
