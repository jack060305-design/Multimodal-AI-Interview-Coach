"""Transcript-based delivery metrics for cloud deploy (no librosa / MediaPipe)."""

from __future__ import annotations

import re

from schemas import (
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


def analyze_transcript_only(transcript: TranscriptResult) -> tuple[FillerWordsMetric, ConfidenceMetric, EyeContactMetric]:
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

    duration_min = max(transcript.duration_seconds / 60.0, 0.1)
    wpm = word_count / duration_min
    pacing_score = 85 if 110 <= wpm <= 170 else 65 if 80 <= wpm <= 200 else 50

    confidence = ConfidenceMetric(
        score=int(round((filler_score + pacing_score) / 2)),
        factors=ConfidenceFactors(
            voice=0.7,
            language=0.75,
            eye_contact=0.7,
            filler_penalty=max(0.0, 1.0 - filler_rate / 100.0),
        ),
    )

    filler = FillerWordsMetric(
        score=filler_score,
        rate=filler_rate,
        count=filler_total,
        top_fillers=sorted(filler_hits, key=filler_hits.get, reverse=True)[:5],
        wpm=round(wpm, 1),
        long_pauses=0,
    )

    eye = EyeContactMetric(
        score=70,
        percentage=70.0,
        comment="Cloud mode: video CV skipped — delivery score uses transcript pacing and fillers.",
    )

    return filler, confidence, eye
