import glob
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


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
class VideoArtifacts:
    audio_path: Path
    frames_dir: Path
    duration_seconds: float
    fps_extracted: float


class VideoProcessor:
    def __init__(self, work_dir: str | Path | None = None):
        if work_dir is None:
            from config import get_settings

            work_dir = get_settings().work_dir
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg = _resolve_binary("ffmpeg")
        self.ffprobe = _resolve_binary("ffprobe")

    def process(self, video_path: str | Path, fps: float = 1.0) -> VideoArtifacts:
        video_path = Path(video_path)
        stem = video_path.stem
        audio_path = self.work_dir / f"{stem}.wav"
        frames_dir = self.work_dir / f"{stem}_frames"
        frames_dir.mkdir(exist_ok=True)

        duration = self._get_duration(video_path)

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

        self._run_ffmpeg(
            [
                self.ffmpeg,
                "-y",
                "-i",
                str(video_path),
                "-vf",
                f"fps={fps}",
                str(frames_dir / "frame_%04d.jpg"),
            ]
        )

        return VideoArtifacts(
            audio_path=audio_path,
            frames_dir=frames_dir,
            duration_seconds=duration,
            fps_extracted=fps,
        )

    def _get_duration(self, video_path: Path) -> float:
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
