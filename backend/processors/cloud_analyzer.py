"""Transcript-based delivery metrics for cloud deploy (no librosa / MediaPipe)."""

from __future__ import annotations

import re

from processors.client_metrics import eye_from_client
from schemas import (
    ClientDeliveryMetrics,
    ConfidenceFactors,
    ConfidenceMetric,
    EyeContactMetric,
    FillerWordsMetric,
    TranscriptResult,
)

FILLERS = {
    "um",
    "uh",
    "like",
    "you know",
    "basically",
    "actually",
    "sort of",
    "kind of",
}

PAUSE_GAP_SEC = 1.5


def _long_pauses(transcript: TranscriptResult) -> int:
    count = 0
    for i in range(1, len(transcript.segments)):
        gap = transcript.segments[i].start - transcript.segments[i - 1].end
        if gap >= PAUSE_GAP_SEC:
            count += 1
    return count


def analyze_transcript_only(
    transcript: TranscriptResult,
    client: ClientDeliveryMetrics | None = None,
) -> tuple[FillerWordsMetric, ConfidenceMetric, EyeContactMetric]:
    text = transcript.text.lower()
    words = re.findall(r"\b[\w']+\b", text)
    word_count = max(len(words), 1)

    filler_hits: dict[str, int] = {}
    for token in words:
        if token in FILLERS:
            filler_hits[token] = filler_hits.get(token, 0) + 1
    for phrase in ("you know", "sort of", "kind of"):
        count = text.count(phrase)
        if count:
            filler_hits[phrase] = filler_hits.get(phrase, 0) + count

    filler_total = sum(filler_hits.values())
    filler_rate = round(100.0 * filler_total / word_count, 1)
    filler_score = max(0, min(100, int(100 - filler_rate * 8)))
    long_pauses = _long_pauses(transcript)

    duration_min = max(transcript.duration_seconds / 60.0, 0.1)
    wpm = word_count / duration_min
    pacing_score = 85 if 110 <= wpm <= 170 else 65 if 80 <= wpm <= 200 else 50
    pause_penalty = min(20, long_pauses * 4)
    pacing_score = max(40, pacing_score - pause_penalty)

    client_eye = eye_from_client(client)
    eye_score_factor = (client_eye.score / 100.0) if client_eye else 0.65

    confidence = ConfidenceMetric(
        score=int(round((filler_score + pacing_score + (client_eye.score if client_eye else 60)) / 3)),
        factors=ConfidenceFactors(
            voice=round(pacing_score / 100.0, 2),
            language=0.75,
            eye_contact=round(eye_score_factor, 2),
            filler_penalty=max(0.0, 1.0 - filler_rate / 100.0),
        ),
    )

    filler = FillerWordsMetric(
        score=filler_score,
        rate=filler_rate,
        count=filler_total,
        top_fillers=sorted(filler_hits, key=filler_hits.get, reverse=True)[:5],
        wpm=round(wpm, 1),
        long_pauses=long_pauses,
    )

    if client_eye:
        eye = client_eye
        eye.source = "browser"
    else:
        eye = EyeContactMetric(
            score=60,
            percentage=60.0,
            source="estimated",
            comment=(
                "Enable camera HUD for live eye-contact tracking. "
                "Using transcript pacing only until browser metrics arrive."
            ),
        )

    return filler, confidence, eye
