import re
from dataclasses import dataclass

import librosa
import numpy as np

from processors.processing_config import (
    AUDIO_HOP_LENGTH,
    AUDIO_N_MFCC,
    AUDIO_SAMPLE_RATE,
    FILLER_WORDS,
    IDEAL_SPEECH_RATE_WPM,
    MAX_PAUSE_DURATION_SEC,
    MIN_PAUSE_DURATION_SEC,
    PAUSE_SILENCE_THRESHOLD_DB,
)
from schemas import ConfidenceFactors, ConfidenceMetric, FillerWordsMetric, TranscriptResult

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
class AcousticFeatures:
    pitch_mean: float
    pitch_std: float
    pitch_min: float
    pitch_max: float
    energy_mean: float
    energy_std: float
    mfcc_mean: float
    mfcc_std: float
    zcr_mean: float
    zcr_std: float


@dataclass
class AudioFeatures:
    wpm: float
    long_pauses: int
    pause_count: int
    avg_pause_duration: float
    max_pause_duration: float
    pitch_mean: float
    pitch_std: float
    rms_mean: float
    rms_std: float
    acoustic_confidence: float


class AudioAnalyzer:
    def __init__(self, long_pause_threshold: float = 1.5):
        self.long_pause_threshold = long_pause_threshold

    def analyze(
        self,
        audio_path: str,
        transcript: TranscriptResult,
        eye_contact_score: int,
    ) -> tuple[FillerWordsMetric, ConfidenceMetric]:
        y, sr = librosa.load(audio_path, sr=AUDIO_SAMPLE_RATE, mono=True)
        acoustic = self._extract_acoustic_features(y, sr)
        pauses = self._detect_pauses(y, sr)
        pause_durations = [end - start for start, end in pauses]

        fillers = self._count_fillers(transcript)
        audio_feats = self._build_audio_features(
            y, sr, transcript, acoustic, pauses, pause_durations
        )
        filler_metric = self._filler_metric(fillers, transcript, audio_feats)
        confidence = self._confidence_metric(
            transcript, audio_feats, eye_contact_score, filler_metric.rate
        )
        return filler_metric, confidence

    def _extract_acoustic_features(self, y: np.ndarray, sr: int) -> AcousticFeatures:
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr, hop_length=AUDIO_HOP_LENGTH)
        pitch_values: list[float] = []
        for t in range(pitches.shape[1]):
            index = int(magnitudes[:, t].argmax())
            pitch = float(pitches[index, t])
            if pitch > 0:
                pitch_values.append(pitch)

        pitch_arr = np.array(pitch_values) if pitch_values else np.array([0.0])
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=AUDIO_N_MFCC)
        rms = librosa.feature.rms(y=y)[0]
        zcr = librosa.feature.zero_crossing_rate(y)[0]

        return AcousticFeatures(
            pitch_mean=float(np.mean(pitch_arr)),
            pitch_std=float(np.std(pitch_arr)),
            pitch_min=float(np.min(pitch_arr)),
            pitch_max=float(np.max(pitch_arr)),
            energy_mean=float(np.mean(rms)),
            energy_std=float(np.std(rms)),
            mfcc_mean=float(np.mean(mfcc)),
            mfcc_std=float(np.std(mfcc)),
            zcr_mean=float(np.mean(zcr)),
            zcr_std=float(np.std(zcr)),
        )

    def _detect_pauses(self, y: np.ndarray, sr: int) -> list[tuple[float, float]]:
        rms = librosa.feature.rms(y=y)[0]
        rms_db = librosa.amplitude_to_db(rms)
        silence_frames = rms_db < PAUSE_SILENCE_THRESHOLD_DB
        times = librosa.frames_to_time(
            np.arange(len(silence_frames)),
            sr=sr,
            hop_length=AUDIO_HOP_LENGTH,
        )

        pauses: list[tuple[float, float]] = []
        in_pause = False
        pause_start = 0.0

        for i, is_silent in enumerate(silence_frames):
            if is_silent and not in_pause:
                pause_start = float(times[i])
                in_pause = True
            elif not is_silent and in_pause:
                pause_end = float(times[i])
                duration = pause_end - pause_start
                if duration >= MIN_PAUSE_DURATION_SEC:
                    pauses.append((pause_start, pause_end))
                in_pause = False

        return pauses

    def _count_fillers(self, transcript: TranscriptResult) -> dict[str, int]:
        text_lower = transcript.text.lower()
        counts: dict[str, int] = {}
        for filler in FILLER_WORDS:
            pattern = r"\b" + re.escape(filler) + r"\b"
            count = len(re.findall(pattern, text_lower))
            if count > 0:
                counts[filler] = count
        return counts

    def _word_count(self, transcript: TranscriptResult) -> int:
        return len(re.findall(r"\b\w+\b", transcript.text))

    def _transcript_long_pauses(self, transcript: TranscriptResult) -> int:
        long_pauses = 0
        for i in range(1, len(transcript.segments)):
            gap = transcript.segments[i].start - transcript.segments[i - 1].end
            if gap >= self.long_pause_threshold:
                long_pauses += 1
        return long_pauses

    def _build_audio_features(
        self,
        y: np.ndarray,
        sr: int,
        transcript: TranscriptResult,
        acoustic: AcousticFeatures,
        pauses: list[tuple[float, float]],
        pause_durations: list[float],
    ) -> AudioFeatures:
        duration_min = max(transcript.duration_seconds / 60, 1e-6)
        word_count = self._word_count(transcript)
        wpm = word_count / duration_min

        transcript_pauses = self._transcript_long_pauses(transcript)
        audio_long_pauses = sum(
            1 for d in pause_durations if d >= self.long_pause_threshold
        )
        long_pauses = max(transcript_pauses, audio_long_pauses)

        acoustic_confidence = self._acoustic_confidence_score(
            acoustic, pause_durations, wpm
        )

        return AudioFeatures(
            wpm=wpm,
            long_pauses=long_pauses,
            pause_count=len(pauses),
            avg_pause_duration=float(np.mean(pause_durations)) if pause_durations else 0.0,
            max_pause_duration=float(max(pause_durations)) if pause_durations else 0.0,
            pitch_mean=acoustic.pitch_mean,
            pitch_std=acoustic.pitch_std,
            rms_mean=acoustic.energy_mean,
            rms_std=acoustic.energy_std,
            acoustic_confidence=acoustic_confidence,
        )

    def _acoustic_confidence_score(
        self,
        acoustic: AcousticFeatures,
        pause_durations: list[float],
        wpm: float,
    ) -> float:
        scores: list[float] = []

        if acoustic.pitch_mean > 0:
            pitch_cv = acoustic.pitch_std / acoustic.pitch_mean
            scores.append(max(0.0, 1.0 - (pitch_cv / 0.5)))

        energy_mean = acoustic.energy_mean
        if energy_mean < 0.01:
            energy_score = energy_mean / 0.01
        elif energy_mean > 0.1:
            energy_score = max(0.0, 1.0 - (energy_mean - 0.1) / 0.1)
        else:
            energy_score = 1.0
        scores.append(energy_score)

        avg_pause = float(np.mean(pause_durations)) if pause_durations else 0.0
        if avg_pause <= 1.0:
            pause_score = 1.0
        elif avg_pause <= MAX_PAUSE_DURATION_SEC:
            pause_score = 1.0 - (
                (avg_pause - 1.0) / (MAX_PAUSE_DURATION_SEC - 1.0)
            )
        else:
            pause_score = 0.3
        scores.append(pause_score)

        ideal_min, ideal_max = IDEAL_SPEECH_RATE_WPM
        if ideal_min <= wpm <= ideal_max:
            rate_score = 1.0
        elif wpm < ideal_min:
            rate_score = max(0.3, wpm / ideal_min)
        else:
            rate_score = max(0.3, ideal_max / wpm)
        scores.append(rate_score)

        return round(float(np.mean(scores)), 3)

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

        acoustic_score = feats.acoustic_confidence * 100
        pitch_stability = max(0, 100 - feats.pitch_std / 2)
        volume_stability = max(0, 100 - feats.rms_std * 500)
        ideal_min, ideal_max = IDEAL_SPEECH_RATE_WPM
        rate_score = (
            100
            if ideal_min <= feats.wpm <= ideal_max
            else 70
            if 100 <= feats.wpm <= 180
            else 50
        )
        voice_score = (
            acoustic_score * 0.35
            + pitch_stability * 0.25
            + volume_stability * 0.2
            + rate_score * 0.2
        )

        eye_norm = float(eye_contact_score)
        filler_penalty = min(100, filler_rate * 10)

        overall = (
            0.35 * voice_score
            + 0.25 * lang_score
            + 0.25 * eye_norm
            + 0.15 * (100 - filler_penalty)
        )

        return ConfidenceMetric(
            score=int(round(overall)),
            factors=ConfidenceFactors(
                voice=round(voice_score, 1),
                language=round(lang_score, 1),
                eye_contact=round(eye_norm, 1),
                filler_penalty=round(filler_penalty, 1),
            ),
        )
