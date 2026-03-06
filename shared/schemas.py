"""Pydantic v2 data models shared across the CubeSat collision prediction system."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AlertLevel(str, Enum):
    """Severity levels for collision risk alerts."""

    ADVISORY = "ADVISORY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class DetectionType(str, Enum):
    """Morphological classification of a detected object in an image frame."""

    streak = "streak"
    point = "point"
    blob = "blob"


class TelemetryPacket(BaseModel):
    """Spacecraft telemetry snapshot associated with a single image frame.

    Attributes:
        timestamp: UTC time when the telemetry was recorded.
        satellite_position: ECI position vector in kilometres (keys: x, y, z).
        velocity: ECI velocity vector in km/s (keys: vx, vy, vz).
        attitude_quaternion: Rotation quaternion [qw, qx, qy, qz].
        frame_id: Identifier tying this packet to a specific :class:`ImageFrame`.
    """

    timestamp: datetime
    satellite_position: dict[str, float] = Field(
        ...,
        description="ECI position vector in km with keys x, y, z.",
        examples=[{"x": 6371.0, "y": 0.0, "z": 0.0}],
    )
    velocity: dict[str, float] = Field(
        ...,
        description="ECI velocity vector in km/s with keys vx, vy, vz.",
        examples=[{"vx": 0.0, "vy": 7.8, "vz": 0.0}],
    )
    attitude_quaternion: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Unit quaternion [qw, qx, qy, qz] describing spacecraft attitude.",
    )
    frame_id: str = Field(..., description="Unique identifier of the associated image frame.")


class ImageFrame(BaseModel):
    """A single captured image frame from the onboard camera.

    Attributes:
        frame_id: Unique identifier for this frame.
        timestamp: UTC time of capture.
        image_data: Base64-encoded raw image bytes.
        width: Image width in pixels.
        height: Image height in pixels.
        exposure_ms: Camera exposure time in milliseconds.
        metadata: Arbitrary additional metadata (e.g. camera gain, temperature).
    """

    frame_id: str = Field(..., description="Unique identifier for this frame.")
    timestamp: datetime
    image_data: str = Field(..., description="Base64-encoded image bytes.")
    width: int = Field(default=640, gt=0, description="Image width in pixels.")
    height: int = Field(default=480, gt=0, description="Image height in pixels.")
    exposure_ms: float = Field(default=10.0, gt=0.0, description="Exposure duration in milliseconds.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary per-frame metadata.")


class DetectionEvent(BaseModel):
    """A single object detection result within an image frame.

    Attributes:
        frame_id: Identifier of the frame in which the detection occurred.
        track_id: Numeric identifier assigned by the tracker to this object.
        bbox: Axis-aligned bounding box with keys x, y, w, h (pixels).
        confidence: Detector confidence score in [0, 1].
        detection_type: Morphological classification of the detected object.
        timestamp: UTC time the detection was produced.
    """

    frame_id: str = Field(..., description="Source frame identifier.")
    track_id: int = Field(..., description="Tracker-assigned object identifier.")
    bbox: dict[str, float] = Field(
        ...,
        description="Bounding box in pixel coordinates with keys x, y, w, h.",
        examples=[{"x": 120.0, "y": 80.0, "w": 15.0, "h": 15.0}],
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score.")
    detection_type: DetectionType
    timestamp: datetime


class TrackObject(BaseModel):
    """State of a tracked object maintained by the tracking filter.

    Attributes:
        track_id: Unique identifier for this track.
        positions: History of [x, y] pixel centroid positions.
        velocities: History of [vx, vy] pixel velocities.
        current_state: Kalman filter state vector [x, y, vx, vy, ax, ay].
        age_in_frames: Number of frames since the track was initialised.
        is_active: Whether the track is currently being updated.
        last_seen: UTC timestamp of the most recent associated detection.
    """

    track_id: int = Field(..., description="Unique track identifier.")
    positions: list[list[float]] = Field(
        default_factory=list,
        description="Ordered history of [x, y] centroid positions in pixels.",
    )
    velocities: list[list[float]] = Field(
        default_factory=list,
        description="Ordered history of [vx, vy] pixel velocities.",
    )
    current_state: list[float] = Field(
        default_factory=lambda: [0.0] * 6,
        min_length=6,
        max_length=6,
        description="Kalman state vector [x, y, vx, vy, ax, ay].",
    )
    age_in_frames: int = Field(default=0, ge=0, description="Frames elapsed since track initialisation.")
    is_active: bool = Field(default=False, description="True if the track is currently active.")
    last_seen: datetime | None = Field(default=None, description="UTC time of the last associated detection.")


class RiskAlert(BaseModel):
    """Collision risk alert generated by the prediction subsystem.

    Attributes:
        alert_id: Unique identifier for this alert.
        track_id: Identifier of the track that triggered the alert.
        alert_level: Severity classification of the risk.
        probability_of_collision: Estimated collision probability in [0, 1].
        time_to_closest_approach: Seconds until the predicted closest approach.
        miss_distance_km: Predicted miss distance at closest approach in km.
        recommended_action: Human-readable mitigation recommendation.
        timestamp: UTC time the alert was generated.
    """

    alert_id: str = Field(..., description="Unique alert identifier.")
    track_id: int = Field(..., description="Track that triggered this alert.")
    alert_level: AlertLevel
    probability_of_collision: float = Field(..., ge=0.0, le=1.0, description="Estimated collision probability.")
    time_to_closest_approach: float = Field(
        ...,
        description="Seconds until the predicted closest approach.",
    )
    miss_distance_km: float = Field(..., ge=0.0, description="Predicted miss distance in km.")
    recommended_action: str = Field(..., description="Human-readable mitigation recommendation.")
    timestamp: datetime
