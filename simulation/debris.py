"""Debris object model and scenario container for the simulation engine."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class DebrisObject:
    """A single piece of orbital debris tracked within a simulation scenario.

    The object maintains its own kinematic state and can render itself onto an
    image array.

    Attributes:
        debris_id: Unique integer identifier for this object.
        x: Current horizontal position in pixels.
        y: Current vertical position in pixels.
        vx: Horizontal velocity in pixels per frame.
        vy: Vertical velocity in pixels per frame.
        size: Approximate radius in pixels used for circular renders.
        brightness: Pixel intensity value in [0, 255] used when drawing.
        debris_type: Morphological class – one of ``"streak"``, ``"point"``,
            or ``"blob"``.
        range_km: Estimated slant range to the object in kilometres.
    """

    debris_id: int
    x: float
    y: float
    vx: float
    vy: float
    size: float = 2.0
    brightness: int = 200
    debris_type: str = "streak"
    range_km: float = 50.0

    def update_position(self, dt: float = 1.0) -> None:
        """Advance the object position by one time step.

        Args:
            dt: Time step multiplier (1.0 = one frame).
        """
        self.x += self.vx * dt
        self.y += self.vy * dt

    def is_visible(self, width: int, height: int) -> bool:
        """Return whether the object is within (or just outside) the frame.

        Args:
            width: Frame width in pixels.
            height: Frame height in pixels.

        Returns:
            ``True`` if the object centre is within a 20-pixel margin of the
            frame boundary.
        """
        margin = 20
        return (
            -margin <= self.x <= width + margin
            and -margin <= self.y <= height + margin
        )

    def render(self, image: np.ndarray) -> np.ndarray:
        """Render this debris object onto *image*.

        * **streak** – a short line segment drawn in the direction opposite to
          the velocity vector, followed by a mild Gaussian blur.
        * **blob** – a filled circle with a slightly larger radius and a
          heavier Gaussian blur to simulate an out-of-focus object.
        * **point** – a small filled circle with no additional blur.

        Args:
            image: Grayscale image array of shape ``(H, W)`` and dtype
                ``uint8`` to draw onto.

        Returns:
            New ``uint8`` image array with this object rendered in.
        """
        img = image.copy()

        if self.debris_type == "streak":
            speed = max(1.0, np.sqrt(self.vx**2 + self.vy**2))
            streak_length = min(40, speed * 5)
            end_x = int(self.x - self.vx / speed * streak_length)
            end_y = int(self.y - self.vy / speed * streak_length)
            x1, y1 = int(self.x), int(self.y)
            cv2.line(img, (x1, y1), (end_x, end_y), int(self.brightness), 2)
            img = cv2.GaussianBlur(img, (3, 3), 0.5)
        elif self.debris_type == "blob":
            cv2.circle(
                img,
                (int(self.x), int(self.y)),
                int(self.size * 2),
                int(self.brightness),
                -1,
            )
            img = cv2.GaussianBlur(img, (5, 5), 1.0)
        else:  # point
            cv2.circle(
                img,
                (int(self.x), int(self.y)),
                max(1, int(self.size)),
                int(self.brightness),
                -1,
            )

        return img


@dataclass
class DebrisScenario:
    """A complete simulation scenario bundling debris objects with timing info.

    Attributes:
        name: Human-readable scenario identifier.
        debris_list: All debris objects active in this scenario.
        duration_frames: Total number of frames the scenario should run for.
        frame_rate: Playback frame rate in frames per second.
    """

    name: str
    debris_list: list[DebrisObject] = field(default_factory=list)
    duration_frames: int = 300
    frame_rate: float = 10.0
