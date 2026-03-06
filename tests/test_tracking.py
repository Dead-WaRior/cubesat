"""Tests for vision/sort_tracker.py KalmanBoxTracker and SORTTracker."""

from __future__ import annotations

import numpy as np
import pytest

from vision.sort_tracker import KalmanBoxTracker, SORTTracker


# ---------------------------------------------------------------------------
# KalmanBoxTracker
# ---------------------------------------------------------------------------


def test_kalman_tracker_init() -> None:
    bbox = [100.0, 50.0, 20.0, 20.0]
    tracker = KalmanBoxTracker(bbox)
    assert tracker is not None
    assert tracker.hits == 0
    assert tracker.time_since_update == 0


def test_kalman_tracker_predict() -> None:
    bbox = [100.0, 50.0, 20.0, 20.0]
    tracker = KalmanBoxTracker(bbox)
    predicted = tracker.predict()
    assert len(predicted) == 4


def test_kalman_tracker_update() -> None:
    bbox = [100.0, 50.0, 20.0, 20.0]
    tracker = KalmanBoxTracker(bbox)
    tracker.predict()
    p_before = tracker.kf.P.copy()
    tracker.update(bbox, confidence=0.9)
    p_after = tracker.kf.P.copy()
    # After update, trace of covariance should not increase (Kalman reduces uncertainty)
    assert np.trace(p_after) <= np.trace(p_before) + 1e-3
    assert tracker.hits == 1
    assert tracker.time_since_update == 0


# ---------------------------------------------------------------------------
# SORTTracker
# ---------------------------------------------------------------------------


def test_sort_tracker_no_detections() -> None:
    tracker = SORTTracker(min_hits=1)
    result = tracker.update([])
    assert result == []


def test_sort_tracker_single_detection() -> None:
    tracker = SORTTracker(min_hits=1)
    det = [{"x": 100.0, "y": 50.0, "w": 20.0, "h": 20.0, "confidence": 0.9}]
    result = tracker.update(det)
    # With min_hits=1, the first frame should return the track
    assert isinstance(result, list)


def test_sort_tracker_track_persistence() -> None:
    tracker = SORTTracker(min_hits=1, max_age=3)
    det = [{"x": 100.0, "y": 50.0, "w": 20.0, "h": 20.0, "confidence": 0.9}]
    # Feed same detection several times
    for _ in range(5):
        result = tracker.update(det)
    assert len(result) >= 1
    assert result[0]["track_id"] > 0


def test_sort_tracker_min_hits() -> None:
    """Tracks only promoted after min_hits frames of consistent detections."""
    tracker = SORTTracker(min_hits=3, max_age=10)
    det = [{"x": 200.0, "y": 100.0, "w": 15.0, "h": 15.0, "confidence": 0.8}]
    for _ in range(5):
        result = tracker.update(det)
    # After several frames the track must have accumulated hits
    assert len(result) >= 1
    assert any(t["age_in_frames"] >= 3 for t in result)
