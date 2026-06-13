"""Sync interview questions from public GitHub feeds (refreshed daily)."""

from __future__ import annotations

import json
import logging
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rubrics.external_feed_loader import (
    CACHE_PATH,
    build_cache_entries,
    feed_status,
    parse_ashish_behavioral_markdown,
)

logger = logging.getLogger(__name__)

FEED_SOURCES = [
    {
        "name": "awesome-behavioral-interviews",
        "url": (
            "https://raw.githubusercontent.com/ashishps1/"
            "awesome-behavioral-interviews/main/README.md"
        ),
        "attribution": "ashishps1/awesome-behavioral-interviews (GitHub)",
    },
]

SYNC_MAX_AGE_HOURS = 24
MAX_QUESTIONS_PER_SOURCE = 80


def _fetch_url(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "interview-coach-question-sync/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _cache_age_hours() -> float | None:
    status = feed_status()
    synced_at = status.get("synced_at")
    if not synced_at:
        return None
    try:
        ts = datetime.fromisoformat(synced_at.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
        return delta.total_seconds() / 3600
    except ValueError:
        return None


def sync_question_feed(*, force: bool = False) -> dict:
    """Download public feeds, merge into question_feed_cache.json."""
    if not force:
        age = _cache_age_hours()
        if age is not None and age < SYNC_MAX_AGE_HOURS:
            return {
                "skipped": True,
                "reason": f"cache fresh ({age:.1f}h old)",
                **feed_status(),
            }

    all_entries: list[dict] = []
    source_results: list[dict] = []

    for source in FEED_SOURCES:
        name = source["name"]
        try:
            text = _fetch_url(source["url"])
            parsed = parse_ashish_behavioral_markdown(text)
            parsed = parsed[:MAX_QUESTIONS_PER_SOURCE]
            entries = build_cache_entries(parsed, name)
            all_entries.extend(entries)
            source_results.append(
                {"name": name, "fetched": len(parsed), "mapped": len(entries), "ok": True}
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("Feed sync failed for %s: %s", name, exc)
            source_results.append({"name": name, "ok": False, "error": str(exc)})

    if not all_entries and not CACHE_PATH.exists():
        return {"ok": False, "error": "no feeds fetched and no existing cache", "sources": source_results}

    if all_entries:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "sources": [s["name"] for s in FEED_SOURCES],
            "attribution": [s.get("attribution", s["name"]) for s in FEED_SOURCES],
            "questions": all_entries,
        }
        CACHE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    from rubrics import sample_rubrics
    from workflows.interview_agents import question_bank

    sample_rubrics.reload_rubrics()
    counts = question_bank.reload_bank()

    status = feed_status()
    return {
        "ok": True,
        "skipped": False,
        "sources": source_results,
        "counts_by_role": counts,
        **status,
    }


def maybe_sync_on_startup() -> None:
    try:
        result = sync_question_feed(force=False)
        if result.get("skipped"):
            logger.info("Question feed cache fresh (%s questions)", result.get("total", 0))
        else:
            logger.info(
                "Question feed synced: %s external questions",
                result.get("total", 0),
            )
    except Exception as exc:
        logger.warning("Startup question feed sync failed: %s", exc)
