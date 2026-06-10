"""
Whisper STT via ONNX Runtime + DirectML for AMD GPUs (e.g. RX 6700 XT on Windows).
Falls back gracefully if DirectML / optimum is not installed.
"""

import logging

import librosa

from schemas import TranscriptResult, TranscriptSegment

logger = logging.getLogger(__name__)

WHISPER_HF_IDS = {
    "tiny": "openai/whisper-tiny",
    "base": "openai/whisper-base",
    "small": "openai/whisper-small",
    "medium": "openai/whisper-medium",
    "large": "openai/whisper-large",
    "large-v2": "openai/whisper-large-v2",
    "large-v3": "openai/whisper-large-v3",
}


class AmdDirectMLWhisperTranscriber:
    def __init__(self, model_size: str | None = None):
        from config import get_settings

        size = model_size or get_settings().whisper_model
        self.model_id = WHISPER_HF_IDS.get(size, "openai/whisper-base")
        self._processor = None
        self._model = None

    def _load(self):
        if self._model is not None:
            return

        from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
        from transformers import AutoProcessor

        logger.info("Loading Whisper ONNX DirectML: %s", self.model_id)
        self._processor = AutoProcessor.from_pretrained(self.model_id)
        self._model = ORTModelForSpeechSeq2Seq.from_pretrained(
            self.model_id,
            provider="DmlExecutionProvider",
        )
        logger.info("Whisper DirectML ready (AMD GPU)")

    def transcribe(self, audio_path: str, language: str | None = None) -> TranscriptResult:
        self._load()

        audio, _ = librosa.load(audio_path, sr=16000, mono=True)
        duration = float(len(audio) / 16000) if len(audio) else 0.0

        inputs = self._processor(
            audio,
            sampling_rate=16000,
            return_tensors="pt",
        )

        gen_kwargs: dict = {"max_new_tokens": 448}
        if language:
            gen_kwargs["forced_decoder_ids"] = self._processor.get_decoder_prompt_ids(
                language=language, task="transcribe"
            )

        predicted_ids = self._model.generate(
            inputs["input_features"],
            **gen_kwargs,
        )
        text = self._processor.batch_decode(
            predicted_ids, skip_special_tokens=True
        )[0].strip()

        segments = [
            TranscriptSegment(
                start=0.0,
                end=duration,
                text=text,
                words=[],
            )
        ]

        return TranscriptResult(
            text=text,
            segments=segments,
            language=language or "en",
            duration_seconds=duration,
        )
