"""Star field generator for synthetic orbital imagery."""

from __future__ import annotations

import numpy as np


class StarField:
    """Generates a synthetic star field background image.

    Stars are placed at reproducible fixed positions derived from *seed*, with
    brightness values sampled from a clipped Gaussian distribution so that
    fainter and brighter stars appear in realistic proportions.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        num_stars: Number of stars to place in the field.
        seed: Random seed for reproducible star placement.
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        num_stars: int = 200,
        seed: int = 42,
    ) -> None:
        self.width = width
        self.height = height
        self.num_stars = num_stars
        self.seed = seed

        rng = np.random.default_rng(seed)
        self._xs: np.ndarray = rng.integers(0, width, size=num_stars)
        self._ys: np.ndarray = rng.integers(0, height, size=num_stars)
        raw_brightness = rng.normal(loc=150.0, scale=60.0, size=num_stars)
        self._brightness: np.ndarray = np.clip(raw_brightness, 50, 255).astype(np.uint8)

    def generate(self) -> np.ndarray:
        """Create the base star field as a grayscale uint8 image.

        Each star is rendered as a single bright pixel.  The returned array
        can be used directly as the background for subsequent debris and noise
        rendering passes.

        Returns:
            Grayscale image array of shape ``(height, width)`` and dtype
            ``uint8`` containing white dots on a near-black background.
        """
        image = np.zeros((self.height, self.width), dtype=np.uint8)
        image[self._ys, self._xs] = self._brightness
        return image
