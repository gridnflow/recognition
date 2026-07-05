"""MediaPipe HandLandmarker 래퍼 + 묵/찌/빠 규칙 기반 분류기."""

import math
from collections import Counter
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

from game import Hand

MODEL_PATH = Path(__file__).parent / "models" / "hand_landmarker.task"

WRIST = 0
# 손가락별 (pip, tip) 랜드마크 인덱스 — 엄지는 접힘 판정이 불안정해 제외
FINGERS = {
    "index": (6, 8),
    "middle": (10, 12),
    "ring": (14, 16),
    "pinky": (18, 20),
}

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # 엄지
    (0, 5), (5, 6), (6, 7), (7, 8),          # 검지
    (5, 9), (9, 10), (10, 11), (11, 12),     # 중지
    (9, 13), (13, 14), (14, 15), (15, 16),   # 약지
    (13, 17), (17, 18), (18, 19), (19, 20),  # 새끼
    (0, 17),
]


def _dist(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y, a.z - b.z)


def classify(landmarks) -> Hand | None:
    """21개 랜드마크에서 묵/찌/빠 판정. 애매하면 None."""
    wrist = landmarks[WRIST]
    extended = set()
    for name, (pip, tip) in FINGERS.items():
        # 손끝이 둘째마디보다 손목에서 충분히 멀면 편 것 — 손 방향에 무관
        if _dist(landmarks[tip], wrist) > _dist(landmarks[pip], wrist) * 1.15:
            extended.add(name)

    n = len(extended)
    if n == 0:
        return Hand.MUK
    if extended == {"index", "middle"}:
        return Hand.JJI
    if n >= 3:
        return Hand.PPA
    return None  # 손가락 1개 등 애매한 모양


class GestureBuffer:
    """캡처 윈도우 동안 프레임별 분류를 모아 다수결로 확정."""

    def __init__(self):
        self._samples: list[Hand] = []

    def reset(self):
        self._samples.clear()

    def add(self, hand: Hand | None):
        if hand is not None:
            self._samples.append(hand)

    def result(self, min_samples: int = 4) -> Hand | None:
        if len(self._samples) < min_samples:
            return None
        return Counter(self._samples).most_common(1)[0][0]


class HandReader:
    """웹캠 프레임(BGR) → (제스처, 랜드마크) 판독기."""

    def __init__(self, model_path: Path = MODEL_PATH):
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts_ms = -1

    def read(self, frame_bgr, timestamp_ms: int):
        """returns (Hand | None, landmarks | None)"""
        # VIDEO 모드는 단조 증가 타임스탬프를 요구
        if timestamp_ms <= self._last_ts_ms:
            timestamp_ms = self._last_ts_ms + 1
        self._last_ts_ms = timestamp_ms

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.hand_landmarks:
            return None, None
        landmarks = result.hand_landmarks[0]
        return classify(landmarks), landmarks

    def close(self):
        self._landmarker.close()


def draw_landmarks(frame_bgr, landmarks):
    """랜드마크 스켈레톤을 프레임에 그림 (디버그/피드백용)."""
    h, w = frame_bgr.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame_bgr, pts[a], pts[b], (0, 200, 120), 2, cv2.LINE_AA)
    for p in pts:
        cv2.circle(frame_bgr, p, 4, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame_bgr, p, 4, (0, 120, 80), 1, cv2.LINE_AA)
