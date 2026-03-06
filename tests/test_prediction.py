"""Tests for prediction layer: coordinate transforms, orbital dynamics, UKF, TCA."""

from __future__ import annotations

import numpy as np
import pytest

from prediction.closest_approach import ClosestApproachCalculator
from prediction.coordinate_transform import CoordinateTransformer
from prediction.orbital_dynamics import j2_perturbation, propagate_state
from prediction.ukf_tracker import UKFTracker

# Typical LEO satellite state [x, y, z, vx, vy, vz] in km / km/s
_SAT_STATE = np.array([6771.0, 0.0, 0.0, 0.0, 7.68, 0.0])
# Nearby debris state (offset ~50 km in x, slightly different velocity)
_DEBRIS_STATE = np.array([6821.0, 0.0, 0.0, 0.0, 7.65, 0.1])


# ---------------------------------------------------------------------------
# CoordinateTransformer
# ---------------------------------------------------------------------------


def test_coordinate_transform_center() -> None:
    transformer = CoordinateTransformer(image_width=640, image_height=480)
    cx, cy = 640 / 2.0, 480 / 2.0
    az, el = transformer.pixel_to_angular(cx, cy)
    assert az == pytest.approx(0.0, abs=1e-10)
    assert el == pytest.approx(0.0, abs=1e-10)


def test_coordinate_transform_edge() -> None:
    transformer = CoordinateTransformer(image_width=640, image_height=480)
    # Top-left corner should give non-zero offsets
    az, el = transformer.pixel_to_angular(0.0, 0.0)
    assert az != pytest.approx(0.0, abs=1e-6)
    assert el != pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# propagate_state
# ---------------------------------------------------------------------------


def test_propagate_state() -> None:
    initial = _SAT_STATE.copy()
    propagated = propagate_state(initial, dt=10.0)
    # Position must change after 10 seconds
    assert not np.allclose(propagated[:3], initial[:3], atol=1e-6)


# ---------------------------------------------------------------------------
# j2_perturbation
# ---------------------------------------------------------------------------


def test_j2_perturbation_nonzero() -> None:
    pos = _SAT_STATE[:3]
    accel = j2_perturbation(pos)
    assert accel.shape == (3,)
    assert np.any(np.abs(accel) > 0.0)


# ---------------------------------------------------------------------------
# UKFTracker
# ---------------------------------------------------------------------------


def test_ukf_tracker_init() -> None:
    tracker = UKFTracker(track_id=1, initial_state=_SAT_STATE.copy())
    assert tracker.track_id == 1
    state = tracker.get_state()
    assert state.shape == (6,)


def test_ukf_predict() -> None:
    tracker = UKFTracker(track_id=2, initial_state=_SAT_STATE.copy(), dt=1.0)
    predicted = tracker.predict(dt=1.0)
    assert predicted.shape == (6,)
    # Position must have moved slightly
    assert not np.allclose(predicted[:3], _SAT_STATE[:3], atol=1e-9)


def test_ukf_update() -> None:
    tracker = UKFTracker(track_id=3, initial_state=_SAT_STATE.copy(), dt=1.0)
    cov_before = np.trace(tracker.get_covariance())
    tracker.predict()
    # Provide measurement close to true state
    measurement = _SAT_STATE[:3] + np.array([0.1, -0.05, 0.02])
    tracker.update(measurement)
    cov_after = np.trace(tracker.get_covariance())
    # Covariance should not be larger after update
    assert cov_after <= cov_before + 1e-3


# ---------------------------------------------------------------------------
# ClosestApproachCalculator
# ---------------------------------------------------------------------------


def test_tca_computation() -> None:
    calc = ClosestApproachCalculator()
    tca_s, miss_km, _, _ = calc.compute_tca(
        _SAT_STATE.copy(),
        _DEBRIS_STATE.copy(),
        max_time=600.0,
        dt=10.0,
    )
    assert tca_s >= 0.0
    # Miss distance should be a reasonable positive number (not NaN, not astronomical)
    assert miss_km >= 0.0
    assert miss_km < 1e6
