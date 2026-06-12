"""Processing constants adapted from multimodal interview analysis pipelines."""

SUPPORTED_VIDEO_FORMATS = (".mp4", ".avi", ".mov", ".mkv", ".webm")

AUDIO_SAMPLE_RATE = 16_000
AUDIO_HOP_LENGTH = 512
AUDIO_N_MFCC = 13

FILLER_WORDS = (
    "um",
    "uh",
    "like",
    "you know",
    "basically",
    "actually",
    "literally",
    "kind of",
    "sort of",
    "i mean",
)

IDEAL_SPEECH_RATE_WPM = (120, 160)
MAX_PAUSE_DURATION_SEC = 3.0
PAUSE_SILENCE_THRESHOLD_DB = -40.0
MIN_PAUSE_DURATION_SEC = 0.5

DEFAULT_FRAME_EXTRACTION_FPS = 1.0
MAX_FRAMES_TO_ANALYZE = 300
