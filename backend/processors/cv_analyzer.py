import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from schemas import EyeContactMetric

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_PATH = Path(__file__).resolve().parent / "face_landmarker.task"


@dataclass
class FrameAnalysis:
    eye_contact: bool
    head_yaw: float
    head_pitch: float
    posture_upright: bool


class CVAnalyzer:
    EYE_THRESHOLD_DEG = 15.0

    def __init__(self):
        self._ensure_model()
        base_options = python.BaseOptions(model_asset_path=str(MODEL_PATH))
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)

    def _ensure_model(self) -> None:
        if MODEL_PATH.exists():
            return
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

    def analyze_frames(self, frames_dir: str | Path) -> EyeContactMetric:
        frames_dir = Path(frames_dir)
        frame_paths = sorted(frames_dir.glob("frame_*.jpg"))
        if not frame_paths:
            return EyeContactMetric(
                score=0,
                percentage=0.0,
                comment="No frames extracted from video.",
            )

        analyses: list[FrameAnalysis] = []
        for path in frame_paths:
            image = cv2.imread(str(path))
            if image is None:
                continue
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.detector.detect(mp_image)
            if not result.face_landmarks:
                analyses.append(
                    FrameAnalysis(
                        eye_contact=False,
                        head_yaw=0.0,
                        head_pitch=0.0,
                        posture_upright=False,
                    )
                )
                continue
            analyses.append(self._analyze_landmarks(result.face_landmarks[0]))

        if not analyses:
            return EyeContactMetric(
                score=0,
                percentage=0.0,
                comment="Could not read any video frames.",
            )

        eye_frames = sum(1 for a in analyses if a.eye_contact)
        percentage = (eye_frames / len(analyses)) * 100

        yaw_values = [abs(a.head_yaw) for a in analyses]
        pitch_values = [abs(a.head_pitch) for a in analyses]
        head_stability = 100 - min(100, np.std(yaw_values + pitch_values) * 5)

        upright_frames = sum(1 for a in analyses if a.posture_upright)
        posture_pct = (upright_frames / len(analyses)) * 100

        score = self._score_eye_contact(percentage)
        comment = self._comment(percentage, head_stability, posture_pct)

        return EyeContactMetric(
            score=score,
            percentage=round(percentage, 1),
            comment=comment,
            head_movement_score=int(round(head_stability)),
            posture_score=int(round(posture_pct)),
        )

    def _analyze_landmarks(self, landmarks) -> FrameAnalysis:
        nose = landmarks[1]
        left_eye = landmarks[33]
        right_eye = landmarks[263]
        chin = landmarks[152]
        forehead = landmarks[10]

        eye_center_x = (left_eye.x + right_eye.x) / 2
        eye_center_y = (left_eye.y + right_eye.y) / 2

        offset_x = (nose.x - eye_center_x) * 100
        offset_y = (nose.y - eye_center_y) * 100

        yaw = math.degrees(math.atan2(offset_x, 50))
        pitch = math.degrees(math.atan2(offset_y, 50))

        eye_contact = (
            abs(yaw) < self.EYE_THRESHOLD_DEG and abs(pitch) < self.EYE_THRESHOLD_DEG
        )

        face_height = abs(forehead.y - chin.y)
        nose_to_chin = abs(nose.y - chin.y)
        posture_upright = face_height > 0.15 and 0.35 < (
            nose_to_chin / max(face_height, 1e-6)
        ) < 0.65

        return FrameAnalysis(
            eye_contact=eye_contact,
            head_yaw=yaw,
            head_pitch=pitch,
            posture_upright=posture_upright,
        )

    def _score_eye_contact(self, percentage: float) -> int:
        if percentage >= 80:
            return 90
        if percentage >= 60:
            return 75
        if percentage >= 40:
            return 55
        return 35

    def _comment(self, eye_pct: float, head_stability: float, posture_pct: float) -> str:
        parts = []
        if eye_pct >= 80:
            parts.append("Excellent eye contact with the camera.")
        elif eye_pct >= 60:
            parts.append("Good eye contact; occasional glances away.")
        else:
            parts.append("Eye contact needs improvement — look at the camera more often.")

        if head_stability < 60:
            parts.append("Head movement is somewhat distracting.")
        if posture_pct < 60:
            parts.append("Posture could be more upright and centered.")

        return " ".join(parts)
