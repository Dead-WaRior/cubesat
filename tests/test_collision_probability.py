"""Tests for prediction/collision_probability.py."""

from __future__ import annotations

import numpy as np
import pytest

from prediction.collision_probability import CollisionProbabilityCalculator

_CALC = CollisionProbabilityCalculator()

# A moderate diagonal covariance (500 m = 0.5 km 1-sigma per axis)
_COV_MODERATE = np.diag([0.25, 0.25, 0.25, 1e-4, 1e-4, 1e-4])
# A tight covariance (100 m = 0.1 km 1-sigma per axis)
_COV_TIGHT = np.diag([0.01, 0.01, 0.01, 1e-6, 1e-6, 1e-6])


def test_pc_zero_when_far() -> None:
    # When hard-body radius is tiny relative to sigma, Pc is near zero
    cov_large = np.diag([100.0, 100.0, 100.0, 1.0, 1.0, 1.0])
    pc = _CALC.compute_pc(
        miss_distance_km=1.0,
        combined_covariance=cov_large,
        combined_size_km=0.0001,  # 100 m hard-body, 10 km sigma → negligible Pc
    )
    assert pc < 0.01


def test_pc_high_when_close() -> None:
    # Very small miss distance (< hard-body radius) → non-trivial Pc
    pc = _CALC.compute_pc(
        miss_distance_km=0.001,
        combined_covariance=_COV_TIGHT,
        combined_size_km=0.01,
    )
    assert pc > 0.0


def test_pc_bounded() -> None:
    for miss in [0.0, 0.01, 0.1, 1.0, 10.0, 100.0]:
        pc = _CALC.compute_pc(
            miss_distance_km=miss,
            combined_covariance=_COV_MODERATE,
            combined_size_km=0.01,
        )
        assert 0.0 <= pc <= 1.0, f"Pc={pc} out of bounds for miss={miss}"


def test_combine_covariances() -> None:
    cov1 = np.eye(6) * 0.1
    cov2 = np.eye(6) * 0.2
    combined = _CALC.combine_covariances(cov1, cov2)
    assert combined.shape == (6, 6)
    # Combined trace should equal the sum of the individual traces
    assert np.trace(combined) == pytest.approx(np.trace(cov1) + np.trace(cov2), rel=1e-6)
    # Each element must be >= the corresponding element in either input
    assert np.all(combined >= cov1 - 1e-12)
    assert np.all(combined >= cov2 - 1e-12)
