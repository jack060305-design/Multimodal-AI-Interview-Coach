"""OpenAI Whisper API transcriber for cloud deploy (no local faster-whisper)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from openai import OpenAI

from schemas import TranscriptResult, TranscriptSegment

logger = logging.getLogger(__name__)


class OpenAIWhisperTranscriber:
    def transcribe(self, audio_path: str) -> TranscriptResult:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required when WHISPER_BACKEND=openai (cloud deploy)."
            )

        client = OpenAI(api_key=api_key)
        path = Path(audio_path)
        with path.open("rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=os.getenv("OPENAI_WHISPER_MODEL", "whisper-1"),
                file=audio_file,
                response_format="verbose_json",
            )

        segments = []
        for seg in getattr(response, "segments", None) or []:
            segments.append(
                TranscriptSegment(
                    start=float(getattr(seg, "start", 0)),
                    end=float(getattr(seg, "end", 0)),
                    text=str(getattr(seg, "text", "")).strip(),
                )
            )

        text = (getattr(response, "text", None) or "").strip()
        duration = float(segments[-1].end) if segments else 0.0
        logger.info("OpenAI Whisper transcribed %s chars from %s", len(text), path.name)

        return TranscriptResult(
            text=text,
            segments=segments,
            language=getattr(response, "language", "en") or "en",
            duration_seconds=duration,
        )
