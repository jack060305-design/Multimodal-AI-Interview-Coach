"""FFmpeg-only media extraction for cloud deploy (no OpenCV)."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CloudMediaArtifacts:
    audio_path: Path
    work_dir: Path


class CloudMediaProcessor:
    def process(self, video_path: str) -> CloudMediaArtifacts:
        work_dir = Path(tempfile.mkdtemp(prefix="interview_cloud_"))
        audio_path = work_dir / "audio.wav"
        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"

        cmd = [
            ffmpeg,
            "-y",
            "-i",
            video_path,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(audio_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg audio extract failed: {result.stderr[-400:]}")

        logger.info("Cloud media: extracted audio to %s", audio_path)
        return CloudMediaArtifacts(audio_path=audio_path, work_dir=work_dir)
