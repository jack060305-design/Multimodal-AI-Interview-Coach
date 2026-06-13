"""Parse optional browser delivery metrics sent with video uploads."""

from __future__ import annotations

import json
from typing import Any

from schemas import ClientDeliveryMetrics, EyeContactMetric


def parse_client_metrics(raw: str | None) -> ClientDeliveryMetrics | None:
    if not raw or not raw.strip():
        return None
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        return ClientDeliveryMetrics.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


def eye_from_client(client: ClientDeliveryMetrics | None) -> EyeContactMetric | None:
    if client is None or client.eye_contact_percentage is None:
        return None
    pct = float(client.eye_contact_percentage)
    score = int(client.eye_contact_score or max(0, min(100, int(round(pct)))))
    return EyeContactMetric(
        score=score,
        percentage=round(pct, 1),
        comment=(
            f"Browser face tracking ({client.frames_analyzed} frames) — "
            "real-time eye contact toward camera."
        ),
    )
