import re
from dataclasses import dataclass

import librosa
import numpy as np

from schemas import ConfidenceFactors, ConfidenceMetric, FillerWordsMetric, TranscriptResult


FILLER_PATTERNS = [
    r"\buh+\b",
    r"\bum+\b",
    r"\blike\b",
    r"\byou know\b",
    r"\bso+\b",
    r"\bbasically\b",
    r"\bactually\b",
    r"\bkind of\b",
    r"\bsort of\b",
    r"\bi mean\b",
]

CONFIDENT_PHRASES = [
    "i believe",
    "definitely",
    "i'm confident",
    "i am confident",
    "clearly",
    "without doubt",
    "i know",
]

UNCERTAIN_PHRASES = [
    "maybe",
    "i think",
    "not sure",
    "i guess",
    "perhaps",
    "might",
    "probably",
]


@dataclass
class AudioFeatures:
    wpm: float
    long_pauses: int
    pitch_mean: float
    pitch_std: float
    rms_mean: float
    rms_std: float


class AudioAnalyzer:
    def __init__(self, long_pause_threshold: float = 1.5):
        self.long_pause_threshold = long_pause_threshold

    def analyze(
        self,
        audio_path: str,
        transcript: TranscriptResult,
        eye_contact_score: int,
    ) -> tuple[FillerWordsMetric, ConfidenceMetric]:
        fillers = self._count_fillers(transcript)
        audio_feats = self._extract_audio_features(audio_path, transcript)
        filler_metric = self._filler_metric(fillers, transcript, audio_feats)
        confidence = self._confidence_metric(
            transcript, audio_feats, eye_contact_score, filler_metric.rate
        )
        return filler_metric, confidence

    def _count_fillers(self, transcript: TranscriptResult) -> dict[str, int]:
        text = transcript.text.lower()
        counts: dict[str, int] = {}
        for pattern in FILLER_PATTERNS:
            label = pattern.strip(r"\b").replace(r"\b", "").replace("+", "")
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            if matches:
                key = label.replace(r"\b", "")
                if key in ("uh", "um"):
                    key = key + "h" if "uh" in pattern else "um"
                counts[key] = counts.get(key, 0) + len(matches)
        return counts

    def _word_count(self, transcript: TranscriptResult) -> int:
        return len(re.findall(r"\b\w+\b", transcript.text))

    def _extract_audio_features(
        self, audio_path: str, transcript: TranscriptResult
    ) -> AudioFeatures:
        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        duration_min = max(transcript.duration_seconds / 60, 1e-6)
        word_count = self._word_count(transcript)
        wpm = word_count / duration_min

        long_pauses = 0
        for i in range(1, len(transcript.segments)):
            gap = transcript.segments[i].start - transcript.segments[i - 1].end
            if gap >= self.long_pause_threshold:
                long_pauses += 1

        f0, _, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=sr,
        )
        f0_valid = f0[~np.isnan(f0)] if f0 is not None else np.array([])
        pitch_mean = float(np.mean(f0_valid)) if len(f0_valid) else 0.0
        pitch_std = float(np.std(f0_valid)) if len(f0_valid) else 0.0

        rms = librosa.feature.rms(y=y)[0]
        rms_mean = float(np.mean(rms))
        rms_std = float(np.std(rms))

        return AudioFeatures(
            wpm=wpm,
            long_pauses=long_pauses,
            pitch_mean=pitch_mean,
            pitch_std=pitch_std,
            rms_mean=rms_mean,
            rms_std=rms_std,
        )

    def _filler_metric(
        self,
        fillers: dict[str, int],
        transcript: TranscriptResult,
        feats: AudioFeatures,
    ) -> FillerWordsMetric:
        total_fillers = sum(fillers.values())
        word_count = max(self._word_count(transcript), 1)
        rate = (total_fillers / word_count) * 100
        top = sorted(fillers.items(), key=lambda x: x[1], reverse=True)
        top_fillers = [k for k, _ in top[:5]]

        if rate <= 2:
            score = 90
        elif rate <= 5:
            score = 70
        elif rate <= 8:
            score = 50
        else:
            score = 30

        return FillerWordsMetric(
            score=score,
            count=total_fillers,
            rate=round(rate, 2),
            top_fillers=top_fillers,
            wpm=round(feats.wpm, 1),
            long_pauses=feats.long_pauses,
        )

    def _confidence_metric(
        self,
        transcript: TranscriptResult,
        feats: AudioFeatures,
        eye_contact_score: int,
        filler_rate: float,
    ) -> ConfidenceMetric:
        text = transcript.text.lower()

        confident = sum(text.count(p) for p in CONFIDENT_PHRASES)
        uncertain = sum(text.count(p) for p in UNCERTAIN_PHRASES)
        lang_score = min(100, 50 + (confident - uncertain) * 10)

        pitch_stability = max(0, 100 - feats.pitch_std / 2)
        volume_stability = max(0, 100 - feats.rms_std * 500)
        rate_score = 100 if 120 <= feats.wpm <= 160 else 70 if 100 <= feats.wpm <= 180 else 50
        voice_score = (pitch_stability * 0.4 + volume_stability * 0.3 + rate_score * 0.3)

        eye_norm = eye_contact_score
        filler_penalty = min(100, filler_rate * 10)

        overall = (
            0.4 * voice_score
            + 0.3 * lang_score
            + 0.2 * eye_norm
            + 0.1 * (100 - filler_penalty)
        )

        return ConfidenceMetric(
            score=int(round(overall)),
            factors=ConfidenceFactors(
                voice=round(voice_score, 1),
                language=round(lang_score, 1),
                eye_contact=round(float(eye_norm), 1),
                filler_penalty=round(filler_penalty, 1),
            ),
        )
