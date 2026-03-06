"""Telemetry packet generator for a simulated low-Earth orbit spacecraft."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np

from shared.schemas import TelemetryPacket

# Physical constants
_EARTH_RADIUS_KM = 6371.0
_ALTITUDE_KM = 400.0
_ORBIT_RADIUS_KM = _EARTH_RADIUS_KM + _ALTITUDE_KM  # ~6 771 km
_ORBITAL_VELOCITY_KMS = 7.7  # km/s (approximate for 400 km circular orbit)
_ORBITAL_PERIOD_S = 2 * math.pi * _ORBIT_RADIUS_KM / _ORBITAL_VELOCITY_KMS  # ~5 520 s


class TelemetryGenerator:
    """Generates realistic spacecraft telemetry for a circular LEO orbit.

    The satellite is modelled on a circular orbit in the equatorial plane.
    Each call to :meth:`generate` advances the orbital anomaly by one frame
    interval (``1 / frame_rate`` seconds) and returns a fresh
    :class:`~shared.schemas.TelemetryPacket`.

    Args:
        initial_position: Optional initial ECI position ``{"x", "y", "z"}``
            in km.  If *None* the satellite starts at ``(r, 0, 0)``.
        initial_velocity: Optional initial ECI velocity ``{"vx", "vy", "vz"}``
            in km/s.  If *None* the velocity is set perpendicular to the
            position for a circular orbit.
        frame_rate: Simulation frame rate in Hz, used to compute the per-frame
            time step.
        seed: Optional integer seed for the attitude jitter RNG.  Pass an
            integer for reproducible runs; *None* (default) yields a different
            sequence each instantiation.
    """

    def __init__(
        self,
        initial_position: dict[str, float] | None = None,
        initial_velocity: dict[str, float] | None = None,
        frame_rate: float = 10.0,
        seed: int | None = None,
    ) -> None:
        self._frame_rate = frame_rate
        self._dt = 1.0 / frame_rate  # seconds per frame

        if initial_position is not None:
            self._pos = np.array(
                [initial_position["x"], initial_position["y"], initial_position["z"]],
                dtype=np.float64,
            )
        else:
            self._pos = np.array([_ORBIT_RADIUS_KM, 0.0, 0.0], dtype=np.float64)

        if initial_velocity is not None:
            self._vel = np.array(
                [initial_velocity["vx"], initial_velocity["vy"], initial_velocity["vz"]],
                dtype=np.float64,
            )
        else:
            # Circular orbit: velocity perpendicular to position in XY plane
            self._vel = np.array([0.0, _ORBITAL_VELOCITY_KMS, 0.0], dtype=np.float64)

        # Compute initial orbital angle from position
        self._angle: float = math.atan2(self._pos[1], self._pos[0])

        # Angular velocity (rad/s)
        self._omega: float = _ORBITAL_VELOCITY_KMS / _ORBIT_RADIUS_KM

        # Base attitude quaternion (identity = nadir-pointing)
        self._base_quat = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)

        self._rng = np.random.default_rng(seed if seed is not None else None)

    def generate(self, frame_id: str, timestamp: datetime) -> TelemetryPacket:
        """Generate a telemetry packet for the current orbital position.

        The orbital angle is advanced by ``dt = 1 / frame_rate`` seconds on
        each call so successive packets represent continuous motion.

        Args:
            frame_id: Identifier of the image frame this packet is paired with.
            timestamp: UTC capture time to embed in the packet.

        Returns:
            A :class:`~shared.schemas.TelemetryPacket` with position, velocity,
            and a slightly jittered attitude quaternion.
        """
        # Advance orbital angle
        self._angle += self._omega * self._dt

        # ECI position (circular, equatorial)
        x = _ORBIT_RADIUS_KM * math.cos(self._angle)
        y = _ORBIT_RADIUS_KM * math.sin(self._angle)
        z = 0.0

        # ECI velocity (perpendicular to radius)
        vx = -_ORBITAL_VELOCITY_KMS * math.sin(self._angle)
        vy = _ORBITAL_VELOCITY_KMS * math.cos(self._angle)
        vz = 0.0

        # Attitude: small random jitter around base quaternion
        jitter = self._rng.normal(0.0, 0.002, size=3)
        qw = 1.0
        qx, qy, qz = jitter
        norm = math.sqrt(qw**2 + qx**2 + qy**2 + qz**2)
        attitude = [qw / norm, qx / norm, qy / norm, qz / norm]

        return TelemetryPacket(
            timestamp=timestamp,
            satellite_position={"x": x, "y": y, "z": z},
            velocity={"vx": vx, "vy": vy, "vz": vz},
            attitude_quaternion=attitude,
            frame_id=frame_id,
        )
