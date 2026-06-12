import logging

from processors.transcriber import WhisperTranscriber
from utils.device import get_accelerator_profile

logger = logging.getLogger(__name__)


def create_transcriber():
    """Pick Whisper backend: OpenAI API (cloud), NVIDIA CUDA, AMD DirectML, or CPU."""
    from config import get_settings

    settings = get_settings()
    if settings.resolved_whisper_backend == "openai":
        from processors.openai_transcriber import OpenAIWhisperTranscriber

        return OpenAIWhisperTranscriber()

    profile = get_accelerator_profile()

    if profile.whisper_backend == "onnx_directml":
        try:
            from processors.whisper_amd import AmdDirectMLWhisperTranscriber

            return AmdDirectMLWhisperTranscriber()
        except Exception as exc:
            logger.warning(
                "AMD DirectML Whisper unavailable (%s) — falling back to CPU faster-whisper",
                exc,
            )

    return WhisperTranscriber()
