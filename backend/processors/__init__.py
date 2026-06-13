__all__ = [
    "AudioAnalyzer",
    "CVAnalyzer",
    "VideoProcessor",
    "WhisperTranscriber",
    "create_transcriber",
]


def __getattr__(name: str):
    if name == "AudioAnalyzer":
        from .audio_analyzer import AudioAnalyzer

        return AudioAnalyzer
    if name == "CVAnalyzer":
        from .cv_analyzer import CVAnalyzer

        return CVAnalyzer
    if name == "VideoProcessor":
        from .video_processor import VideoProcessor

        return VideoProcessor
    if name == "WhisperTranscriber":
        from .transcriber import WhisperTranscriber

        return WhisperTranscriber
    if name == "create_transcriber":
        from .transcriber_factory import create_transcriber

        return create_transcriber
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
