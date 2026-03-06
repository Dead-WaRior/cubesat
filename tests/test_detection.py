"""Tests for vision/streak_detector.py and vision/detector.py."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from vision.detector import DebrisDetector
from vision.streak_detector import StreakDetector


# ---------------------------------------------------------------------------
# StreakDetector
# ---------------------------------------------------------------------------


def test_streak_detection_on_blank() -> None:
    detector = StreakDetector()
    blank = np.zeros((480, 640), dtype=np.uint8)
    detections = detector.detect(blank)
    assert detections == []


def test_streak_detection_on_line_image() -> None:
    detector = StreakDetector(min_line_length=15)
    image = np.zeros((480, 640), dtype=np.uint8)
    # Draw a bright diagonal line long enough to be detected
    cv2.line(image, (50, 100), (350, 300), 255, 2)
    detections = detector.detect(image)
    assert len(detections) >= 1
    det = detections[0]
    assert det["detection_type"] == "streak"
    assert det["confidence"] > 0.0


# ---------------------------------------------------------------------------
# DebrisDetector
# ---------------------------------------------------------------------------


def test_debris_detector_init() -> None:
    detector = DebrisDetector(use_yolo=False)
    assert detector is not None


def test_debris_detector_blank() -> None:
    detector = DebrisDetector(use_yolo=False, confidence_threshold=0.1)
    blank = np.zeros((480, 640), dtype=np.uint8)
    detections = detector.detect(blank)
    # Blank image: no features → empty or very minimal detections
    assert isinstance(detections, list)


# ---------------------------------------------------------------------------
# IoU computation
# ---------------------------------------------------------------------------


def test_iou_computation() -> None:
    detector = DebrisDetector(use_yolo=False)
    box1 = {"x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0}
    box2 = {"x": 5.0, "y": 5.0, "w": 10.0, "h": 10.0}
    iou = detector._compute_iou(box1, box2)
    assert iou > 0.0


def test_iou_non_overlapping() -> None:
    detector = DebrisDetector(use_yolo=False)
    box1 = {"x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0}
    box2 = {"x": 50.0, "y": 50.0, "w": 10.0, "h": 10.0}
    iou = detector._compute_iou(box1, box2)
    assert iou == pytest.approx(0.0, abs=1e-6)
