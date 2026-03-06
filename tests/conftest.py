"""Pytest fixtures shared across the CubeSat test suite."""

from __future__ import annotations

import base64
from datetime import datetime, timezone

import numpy as np
import pytest

from shared.schemas import (
    AlertLevel,
    DetectionEvent,
    DetectionType,
    ImageFrame,
    RiskAlert,
    TelemetryPacket,
    TrackObject,
)
from simulation.star_field import StarField


@pytest.fixture
def sample_telemetry() -> TelemetryPacket:
    """Return a TelemetryPacket with realistic LEO values."""
    return TelemetryPacket(
        timestamp=datetime.now(timezone.utc),
        satellite_position={"x": 6771.0, "y": 0.0, "z": 0.0},
        velocity={"vx": 0.0, "vy": 7.68, "vz": 0.0},
        attitude_quaternion=[1.0, 0.0, 0.0, 0.0],
        frame_id="frame_000001_abcd1234",
    )


@pytest.fixture
def sample_image_frame() -> ImageFrame:
    """Return an ImageFrame with a 640x480 black image (base64 encoded)."""
    black = np.zeros((480, 640), dtype=np.uint8)
    import cv2

    _, buf = cv2.imencode(".png", black)
    image_b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    return ImageFrame(
        frame_id="frame_000001_abcd1234",
        timestamp=datetime.now(timezone.utc),
        image_data=image_b64,
        width=640,
        height=480,
        exposure_ms=10.0,
    )


@pytest.fixture
def sample_detection_event() -> DetectionEvent:
    """Return a DetectionEvent with typical values."""
    return DetectionEvent(
        frame_id="frame_000001_abcd1234",
        track_id=1,
        bbox={"x": 120.0, "y": 80.0, "w": 15.0, "h": 15.0},
        confidence=0.87,
        detection_type=DetectionType.streak,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_track_object() -> TrackObject:
    """Return a TrackObject with default values."""
    return TrackObject(
        track_id=1,
        positions=[[120.0, 80.0], [122.0, 81.0]],
        velocities=[[2.0, 1.0]],
        current_state=[120.0, 80.0, 2.0, 1.0, 0.0, 0.0],
        age_in_frames=2,
        is_active=True,
        last_seen=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_risk_alert() -> RiskAlert:
    """Return a RiskAlert at WARNING level."""
    return RiskAlert(
        alert_id="alert-0001",
        track_id=1,
        alert_level=AlertLevel.WARNING,
        probability_of_collision=2e-4,
        time_to_closest_approach=1800.0,
        miss_distance_km=3.5,
        recommended_action="Review maneuver plan, prepare avoidance burn",
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def blank_image() -> np.ndarray:
    """Return a 480x640 numpy uint8 zeros array."""
    return np.zeros((480, 640), dtype=np.uint8)


@pytest.fixture
def star_image() -> np.ndarray:
    """Return a realistic star field numpy array."""
    return StarField(width=640, height=480, seed=42).generate()
