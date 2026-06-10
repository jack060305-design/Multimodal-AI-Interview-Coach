import logging
from typing import Any

from schemas import TranscriptResult, TranscriptSegment
from utils.device import get_accelerator_profile

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ):
        from config import get_settings

        s = get_settings()
        profile = get_accelerator_profile()

        self.model_size = model_size or s.whisper_model
        self.device = device or profile.whisper_device
        self.compute_type = compute_type or profile.whisper_compute
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model

        from faster_whisper import WhisperModel

        try:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info(
                "Whisper loaded: model=%s device=%s compute=%s",
                self.model_size,
                self.device,
                self.compute_type,
            )
            return self._model
        except Exception as exc:
            if self.device == "cuda":
                logger.warning(
                    "Whisper GPU load failed (%s) — falling back to CPU int8", exc
                )
                self.device = "cpu"
                self.compute_type = "int8"
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                )
                return self._model
            raise

    def transcribe(self, audio_path: str, language: str | None = None) -> TranscriptResult:
        model = self._load_model()
        segments_iter, info = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True,
        )

        segments: list[TranscriptSegment] = []
        full_text_parts: list[str] = []

        for seg in segments_iter:
            words = []
            if seg.words:
                words = [
                    {
                        "word": w.word.strip(),
                        "start": w.start,
                        "end": w.end,
                        "probability": getattr(w, "probability", None),
                    }
                    for w in seg.words
                ]

            segments.append(
                TranscriptSegment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                    words=words,
                )
            )
            full_text_parts.append(seg.text.strip())

        duration = segments[-1].end if segments else 0.0

        return TranscriptResult(
            text=" ".join(full_text_parts),
            segments=segments,
            language=info.language or "en",
            duration_seconds=duration,
        )
