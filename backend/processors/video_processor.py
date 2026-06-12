import glob
import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from processors.processing_config import (
    DEFAULT_FRAME_EXTRACTION_FPS,
    SUPPORTED_VIDEO_FORMATS,
)

logger = logging.getLogger(__name__)


def _resolve_binary(name: str) -> str:
    override = os.getenv(name.upper()) or os.getenv(f"{name.upper()}_PATH")
    if override and Path(override).exists():
        return override

    found = shutil.which(name)
    if found:
        return found

    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        pattern = os.path.join(
            local,
            "Microsoft",
            "WinGet",
            "Packages",
            "Gyan.FFmpeg*",
            "ffmpeg*",
            "bin",
            f"{name}.exe",
        )
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

    return name


@dataclass
class VideoMetadata:
    filename: str
    duration_seconds: float
    fps: float
    frame_count: int
    resolution: tuple[int, int]


@dataclass
class VideoArtifacts:
    audio_path: Path
    frames_dir: Path
    duration_seconds: float
    fps_extracted: float
    metadata: VideoMetadata
    frames_extracted: int


class VideoProcessor:
    def __init__(self, work_dir: str | Path | None = None):
        if work_dir is None:
            from config import get_settings

            work_dir = get_settings().work_dir
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg = _resolve_binary("ffmpeg")
        self.ffprobe = _resolve_binary("ffprobe")

    def process(
        self,
        video_path: str | Path,
        fps: float = DEFAULT_FRAME_EXTRACTION_FPS,
    ) -> VideoArtifacts:
        video_path = Path(video_path)
        self._validate_video(video_path)

        stem = video_path.stem
        audio_path = self.work_dir / f"{stem}.wav"
        frames_dir = self.work_dir / f"{stem}_frames"
        frames_dir.mkdir(exist_ok=True)

        metadata = self._read_metadata(video_path)
        duration = metadata.duration_seconds or self._get_duration_ffprobe(video_path)
        if duration > 0:
            metadata.duration_seconds = duration

        self._extract_audio_ffmpeg(video_path, audio_path)
        frames_extracted = self._extract_frames_opencv(
            video_path, frames_dir, fps=fps, metadata=metadata
        )

        return VideoArtifacts(
            audio_path=audio_path,
            frames_dir=frames_dir,
            duration_seconds=duration,
            fps_extracted=fps,
            metadata=metadata,
            frames_extracted=frames_extracted,
        )

    def _validate_video(self, video_path: Path) -> None:
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if video_path.suffix.lower() not in SUPPORTED_VIDEO_FORMATS:
            raise ValueError(
                f"Unsupported video format: {video_path.suffix}. "
                f"Supported: {list(SUPPORTED_VIDEO_FORMATS)}"
            )

    def _read_metadata(self, video_path: Path) -> VideoMetadata:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            duration = frame_count / fps if fps > 0 else 0.0

            return VideoMetadata(
                filename=video_path.name,
                duration_seconds=duration,
                fps=fps,
                frame_count=frame_count,
                resolution=(width, height),
            )
        finally:
            cap.release()

    def _extract_audio_ffmpeg(self, video_path: Path, audio_path: Path) -> None:
        logger.info("Extracting audio: %s -> %s", video_path.name, audio_path.name)
        self._run_ffmpeg(
            [
                self.ffmpeg,
                "-y",
                "-i",
                str(video_path),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                str(audio_path),
            ]
        )

    def _extract_frames_opencv(
        self,
        video_path: Path,
        frames_dir: Path,
        fps: float,
        metadata: VideoMetadata,
    ) -> int:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video for frame extraction: {video_path}")

        source_fps = metadata.fps or float(cap.get(cv2.CAP_PROP_FPS) or 1.0)
        frame_interval = max(1, int(round(source_fps / fps))) if fps > 0 else 1

        logger.info(
            "Extracting frames at %.2f FPS (interval=%d) to %s",
            fps,
            frame_interval,
            frames_dir,
        )

        extracted = 0
        frame_idx = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % frame_interval == 0:
                    frame_path = frames_dir / f"frame_{extracted:04d}.jpg"
                    cv2.imwrite(str(frame_path), frame)
                    extracted += 1
                frame_idx += 1
        finally:
            cap.release()

        logger.info("Extracted %d frames from %s", extracted, video_path.name)
        return extracted

    def extract_frame_at_timestamp(
        self, video_path: str | Path, timestamp: float
    ) -> np.ndarray | None:
        video_path = Path(video_path)
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return None

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if fps <= 0:
                return None

            frame_number = int(timestamp * fps)
            if frame_number >= frame_count:
                return None

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            return frame if ret else None
        finally:
            cap.release()

    def _get_duration_ffprobe(self, video_path: Path) -> float:
        result = subprocess.run(
            [
                self.ffprobe,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))

    def _run_ffmpeg(self, cmd: list[str]) -> None:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
