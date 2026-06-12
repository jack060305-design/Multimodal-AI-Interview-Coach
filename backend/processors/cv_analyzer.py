import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from processors.processing_config import MAX_FRAMES_TO_ANALYZE
from schemas import EyeContactMetric

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_PATH = Path(__file__).resolve().parent / "face_landmarker.task"


@dataclass
class FrameFaceData:
    eye_contact_score: float
    face_position: tuple[float, float]
    nose_y: float
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

        if len(frame_paths) > MAX_FRAMES_TO_ANALYZE:
            step = max(1, len(frame_paths) // MAX_FRAMES_TO_ANALYZE)
            frame_paths = frame_paths[::step][:MAX_FRAMES_TO_ANALYZE]

        frame_data: list[FrameFaceData] = []
        frames_analyzed = 0
        frames_with_face = 0

        for path in frame_paths:
            image = cv2.imread(str(path))
            if image is None:
                continue

            frames_analyzed += 1
            data = self._detect_face(image)
            if data is None:
                frame_data.append(
                    FrameFaceData(
                        eye_contact_score=0.0,
                        face_position=(0.0, 0.0),
                        nose_y=0.0,
                        posture_upright=False,
                    )
                )
                continue

            frames_with_face += 1
            frame_data.append(data)

        if not frame_data:
            return EyeContactMetric(
                score=0,
                percentage=0.0,
                comment="Could not read any video frames.",
            )

        eye_scores = [d.eye_contact_score for d in frame_data if d.eye_contact_score > 0]
        eye_contact_ratio = float(np.mean(eye_scores)) if eye_scores else 0.0
        percentage = eye_contact_ratio * 100

        face_positions = [
            d.face_position for d in frame_data if d.face_position != (0.0, 0.0)
        ]
        head_stability = self._head_stability_score(face_positions)
        expression_variance = self._expression_variance_score(frame_data)
        face_detection_rate = (
            frames_with_face / frames_analyzed if frames_analyzed > 0 else 0.0
        )

        upright_frames = sum(1 for d in frame_data if d.posture_upright)
        posture_pct = (upright_frames / len(frame_data)) * 100

        engagement = (
            0.5 * eye_contact_ratio
            + 0.3 * head_stability
            + 0.2 * face_detection_rate
        )
        score = self._score_engagement(engagement, percentage)
        comment = self._comment(percentage, head_stability * 100, posture_pct)

        return EyeContactMetric(
            score=score,
            percentage=round(percentage, 1),
            comment=comment,
            head_movement_score=int(round(head_stability * 100)),
            posture_score=int(round(posture_pct)),
        )

    def _detect_face(self, image: np.ndarray) -> FrameFaceData | None:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.detector.detect(mp_image)
        if not result.face_landmarks:
            return None

        landmarks = result.face_landmarks[0]
        h, w = image.shape[:2]

        left_eye = np.array(
            [(landmarks[33].x * w, landmarks[33].y * h), (landmarks[133].x * w, landmarks[133].y * h)]
        )
        right_eye = np.array(
            [(landmarks[362].x * w, landmarks[362].y * h), (landmarks[263].x * w, landmarks[263].y * h)]
        )
        nose = landmarks[1]
        chin = landmarks[152]
        forehead = landmarks[10]

        eyes_center = (left_eye.mean(axis=0) + right_eye.mean(axis=0)) / 2
        image_center = np.array([w / 2, h / 2])
        distance = float(np.linalg.norm(eyes_center - image_center))
        max_distance = float(np.linalg.norm(image_center))
        gaze_score = max(0.0, 1.0 - (distance / max(max_distance, 1e-6)))

        offset_x = (nose.x - (landmarks[33].x + landmarks[263].x) / 2) * 100
        offset_y = (nose.y - (landmarks[33].y + landmarks[263].y) / 2) * 100
        yaw = math.degrees(math.atan2(offset_x, 50))
        pitch = math.degrees(math.atan2(offset_y, 50))
        landmark_eye_contact = (
            abs(yaw) < self.EYE_THRESHOLD_DEG and abs(pitch) < self.EYE_THRESHOLD_DEG
        )
        landmark_score = 1.0 if landmark_eye_contact else 0.0
        eye_contact_score = 0.6 * gaze_score + 0.4 * landmark_score

        face_height = abs(forehead.y - chin.y)
        nose_to_chin = abs(nose.y - chin.y)
        posture_upright = face_height > 0.15 and 0.35 < (
            nose_to_chin / max(face_height, 1e-6)
        ) < 0.65

        return FrameFaceData(
            eye_contact_score=eye_contact_score,
            face_position=(float(nose.x * w), float(nose.y * h)),
            nose_y=float(nose.y * h),
            posture_upright=posture_upright,
        )

    def _head_stability_score(self, positions: list[tuple[float, float]]) -> float:
        if len(positions) < 2:
            return 1.0

        movements = []
        for i in range(1, len(positions)):
            prev = np.array(positions[i - 1])
            curr = np.array(positions[i])
            movements.append(float(np.linalg.norm(curr - prev)))

        avg_movement = float(np.mean(movements))
        normalized = min(avg_movement / 50.0, 1.0)
        return max(0.0, 1.0 - normalized)

    def _expression_variance_score(self, frame_data: list[FrameFaceData]) -> float:
        nose_positions = [d.nose_y for d in frame_data if d.nose_y > 0]
        if len(nose_positions) < 5:
            return 0.5

        variance = float(np.var(nose_positions))
        normalized = min(variance / 100.0, 1.0)
        if 0.2 <= normalized <= 0.4:
            return 0.9
        if normalized < 0.2:
            return 0.6
        return max(0.3, 1.0 - normalized)

    def _score_engagement(self, engagement: float, eye_pct: float) -> int:
        blended = engagement * 0.6 + (eye_pct / 100) * 0.4
        if blended >= 0.8:
            return 90
        if blended >= 0.6:
            return 75
        if blended >= 0.4:
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
