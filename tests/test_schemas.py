"""Tests for shared/schemas.py Pydantic data models."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from shared.schemas import (
    AlertLevel,
    DetectionEvent,
    DetectionType,
    ImageFrame,
    RiskAlert,
    TelemetryPacket,
    TrackObject,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# TelemetryPacket
# ---------------------------------------------------------------------------


def test_telemetry_packet_creation() -> None:
    packet = TelemetryPacket(
        timestamp=_now(),
        satellite_position={"x": 6771.0, "y": 0.0, "z": 0.0},
        velocity={"vx": 0.0, "vy": 7.68, "vz": 0.0},
        attitude_quaternion=[1.0, 0.0, 0.0, 0.0],
        frame_id="frame_000001",
    )
    assert packet.frame_id == "frame_000001"
    assert packet.satellite_position["x"] == 6771.0
    assert len(packet.attitude_quaternion) == 4


def test_telemetry_packet_invalid() -> None:
    with pytest.raises(ValidationError):
        # Missing required fields: timestamp, satellite_position, velocity, attitude_quaternion, frame_id
        TelemetryPacket()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# ImageFrame
# ---------------------------------------------------------------------------


def test_image_frame_defaults() -> None:
    frame = ImageFrame(
        frame_id="f1",
        timestamp=_now(),
        image_data="abc123",
    )
    assert frame.width == 640
    assert frame.height == 480
    assert frame.exposure_ms == 10.0


def test_image_frame_custom_dimensions() -> None:
    frame = ImageFrame(
        frame_id="f2",
        timestamp=_now(),
        image_data="abc123",
        width=1280,
        height=960,
    )
    assert frame.width == 1280
    assert frame.height == 960


# ---------------------------------------------------------------------------
# DetectionEvent
# ---------------------------------------------------------------------------


def test_detection_event_types() -> None:
    for det_type in DetectionType:
        event = DetectionEvent(
            frame_id="f1",
            track_id=1,
            bbox={"x": 10.0, "y": 20.0, "w": 5.0, "h": 5.0},
            confidence=0.9,
            detection_type=det_type,
            timestamp=_now(),
        )
        assert event.detection_type == det_type


# ---------------------------------------------------------------------------
# RiskAlert
# ---------------------------------------------------------------------------


def test_risk_alert_levels() -> None:
    for level in AlertLevel:
        alert = RiskAlert(
            alert_id="a1",
            track_id=1,
            alert_level=level,
            probability_of_collision=1e-4,
            time_to_closest_approach=3600.0,
            miss_distance_km=5.0,
            recommended_action="Monitor",
            timestamp=_now(),
        )
        assert alert.alert_level == level


# ---------------------------------------------------------------------------
# TrackObject
# ---------------------------------------------------------------------------


def test_track_object_defaults() -> None:
    track = TrackObject(track_id=42)
    assert track.age_in_frames == 0
    assert track.is_active is False
    assert track.last_seen is None
    assert len(track.current_state) == 6


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------


def test_serialization_roundtrip() -> None:
    packet = TelemetryPacket(
        timestamp=_now(),
        satellite_position={"x": 6771.0, "y": 100.0, "z": -50.0},
        velocity={"vx": -0.5, "vy": 7.68, "vz": 0.1},
        attitude_quaternion=[0.9999, 0.001, 0.002, 0.003],
        frame_id="frame_roundtrip",
    )
    json_str = packet.model_dump_json()
    data = json.loads(json_str)
    restored = TelemetryPacket.model_validate(data)
    assert restored.frame_id == packet.frame_id
    assert restored.satellite_position == packet.satellite_position
    assert restored.velocity == packet.velocity
