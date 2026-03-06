"""Coordinate transformations between pixel space, angular offsets, and ECI frame."""

from __future__ import annotations

import math

import numpy as np

# Camera defaults
FOV_DEG: float = 10.0
FOCAL_LENGTH_MM: float = 50.0
SENSOR_WIDTH_MM: float = 6.4
SENSOR_HEIGHT_MM: float = 4.8


class CoordinateTransformer:
    """Transforms detections from pixel coordinates into ECI frame positions.

    The pipeline proceeds in two stages:
    1. Pixel → angular offsets (azimuth / elevation relative to boresight).
    2. Angular offsets + slant range → approximate ECI position by shifting
       the host satellite's known ECI position along the line-of-sight unit
       vector derived from the angular offsets.

    Args:
        fov_deg: Horizontal field-of-view of the camera in degrees.
        image_width: Image width in pixels.
        image_height: Image height in pixels.
    """

    def __init__(
        self,
        fov_deg: float = FOV_DEG,
        image_width: int = 640,
        image_height: int = 480,
    ) -> None:
        self.fov_deg = fov_deg
        self.image_width = image_width
        self.image_height = image_height

        # Angular resolution per pixel (radians)
        fov_rad = math.radians(fov_deg)
        self._rad_per_px_x: float = fov_rad / image_width
        # Maintain square pixels by deriving vertical FOV from aspect ratio
        fov_y_rad = fov_rad * (image_height / image_width)
        self._rad_per_px_y: float = fov_y_rad / image_height

    # ------------------------------------------------------------------
    # Forward transforms
    # ------------------------------------------------------------------

    def pixel_to_angular(self, px: float, py: float) -> tuple[float, float]:
        """Convert pixel coordinates to angular offsets from the image boresight.

        The boresight is defined as the image centre.  Positive azimuth is to
        the right (increasing *x*) and positive elevation is upward (decreasing
        *y* in image coordinates).

        Args:
            px: Horizontal pixel coordinate (0 = left edge).
            py: Vertical pixel coordinate (0 = top edge).

        Returns:
            Tuple of ``(azimuth_rad, elevation_rad)`` angular offsets.
        """
        cx = self.image_width / 2.0
        cy = self.image_height / 2.0
        azimuth_rad = (px - cx) * self._rad_per_px_x
        elevation_rad = -(py - cy) * self._rad_per_px_y  # flip y-axis
        return azimuth_rad, elevation_rad

    def angular_to_eci(
        self,
        az: float,
        el: float,
        range_km: float,
        satellite_pos: dict[str, float],
    ) -> np.ndarray:
        """Compute an approximate ECI position from angular offsets and slant range.

        The implementation uses a simple body-frame approximation: the
        line-of-sight unit vector is constructed from the angular offsets (az,
        el) and scaled by *range_km*, then added to the satellite's ECI
        position.  No full attitude rotation is applied because the spacecraft
        attitude is not passed here; callers needing full attitude accuracy
        should rotate the result appropriately.

        Args:
            az: Azimuth offset from boresight in radians.
            el: Elevation offset from boresight in radians.
            range_km: Estimated slant range to the object in km.
            satellite_pos: Host satellite ECI position in km with keys
                ``x``, ``y``, ``z``.

        Returns:
            Approximate ECI position of the detected object as a
            ``np.ndarray`` of shape ``(3,)`` in km.
        """
        # Line-of-sight unit vector in a generic "camera" frame aligned with ECI axes
        los = np.array([
            math.cos(el) * math.cos(az),
            math.cos(el) * math.sin(az),
            math.sin(el),
        ])
        sat_pos = np.array([satellite_pos["x"], satellite_pos["y"], satellite_pos["z"]])
        return sat_pos + range_km * los

    # ------------------------------------------------------------------
    # Inverse transform
    # ------------------------------------------------------------------

    def eci_to_pixel(
        self,
        eci_pos: np.ndarray,
        satellite_pos: dict[str, float],
    ) -> tuple[float, float]:
        """Project an ECI position back to pixel coordinates.

        Args:
            eci_pos: ECI position of the target object in km, shape ``(3,)``.
            satellite_pos: Host satellite ECI position in km with keys
                ``x``, ``y``, ``z``.

        Returns:
            Tuple of ``(px, py)`` pixel coordinates.  Objects outside the
            camera FOV are clamped to the image boundary.

        Raises:
            ValueError: If the target is at the same position as the satellite.
        """
        sat_pos = np.array([satellite_pos["x"], satellite_pos["y"], satellite_pos["z"]])
        delta = eci_pos - sat_pos
        norm = np.linalg.norm(delta)
        if norm < 1e-12:
            raise ValueError("Target and satellite positions are coincident.")
        los = delta / norm

        # Recover azimuth and elevation from the unit vector
        el = math.asin(float(np.clip(los[2], -1.0, 1.0)))
        az = math.atan2(float(los[1]), float(los[0]))

        cx = self.image_width / 2.0
        cy = self.image_height / 2.0
        px = cx + az / self._rad_per_px_x
        py = cy - el / self._rad_per_px_y  # flip y-axis back
        return px, py
