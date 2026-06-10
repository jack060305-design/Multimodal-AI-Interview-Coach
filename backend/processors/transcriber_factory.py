import logging

from processors.transcriber import WhisperTranscriber
from utils.device import get_accelerator_profile

logger = logging.getLogger(__name__)


def create_transcriber():
    """Pick Whisper backend: NVIDIA CUDA, AMD DirectML, or CPU — never crashes."""
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
