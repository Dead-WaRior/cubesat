"""Noise injection functions for synthetic orbital imagery."""

from __future__ import annotations

import numpy as np


def add_gaussian_noise(
    image: np.ndarray,
    sigma: float = 2.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Add additive Gaussian noise to *image*.

    Args:
        image: Input grayscale image of dtype ``uint8``.
        sigma: Standard deviation of the Gaussian noise in pixel intensity
            units.
        rng: Optional NumPy random generator for reproducible results.  A
            fresh default generator is used when *None*.

    Returns:
        New ``uint8`` image with noise added (values clamped to [0, 255]).
    """
    _rng = rng if rng is not None else np.random.default_rng()
    noise = _rng.normal(0.0, sigma, image.shape)
    noisy = image.astype(np.float32) + noise
    return np.clip(noisy, 0, 255).astype(np.uint8)


def add_hot_pixels(
    image: np.ndarray,
    density: float = 0.001,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Inject random hot (saturated bright) pixels into *image*.

    Hot pixels simulate sensor defects common in space-grade imagers.

    Args:
        image: Input grayscale image of dtype ``uint8``.
        density: Fraction of pixels to set as hot pixels.  For example
            ``0.001`` means 0.1 % of all pixels.
        rng: Optional NumPy random generator for reproducible results.

    Returns:
        New ``uint8`` image with hot pixels applied.
    """
    _rng = rng if rng is not None else np.random.default_rng()
    result = image.copy()
    total_pixels = image.shape[0] * image.shape[1]
    num_hot = max(0, int(total_pixels * density))
    if num_hot == 0:
        return result
    rows = _rng.integers(0, image.shape[0], size=num_hot)
    cols = _rng.integers(0, image.shape[1], size=num_hot)
    result[rows, cols] = 255
    return result


def add_cosmic_ray(
    image: np.ndarray,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Add a single cosmic-ray event (bright streak or point spike) to *image*.

    The event is chosen randomly to be either a short linear streak (the more
    common morphology) or a single saturated point.

    Args:
        image: Input grayscale image of dtype ``uint8``.
        rng: Optional NumPy random generator for reproducible results.

    Returns:
        New ``uint8`` image with one cosmic-ray event added.
    """
    import cv2  # local import to avoid hard dependency at module level

    _rng = rng if rng is not None else np.random.default_rng()
    result = image.copy()
    h, w = result.shape[:2]

    if _rng.random() < 0.7:
        # Linear streak
        x0 = int(_rng.integers(0, w))
        y0 = int(_rng.integers(0, h))
        angle = float(_rng.uniform(0, np.pi))
        length = int(_rng.integers(5, 31))
        x1 = int(x0 + np.cos(angle) * length)
        y1 = int(y0 + np.sin(angle) * length)
        cv2.line(result, (x0, y0), (x1, y1), 255, 1)
    else:
        # Single saturated dot
        x0 = int(_rng.integers(0, w))
        y0 = int(_rng.integers(0, h))
        result[y0, x0] = 255

    return result


def apply_all_noise(
    image: np.ndarray,
    config: dict,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Apply a full noise pipeline to *image* according to *config*.

    Config keys (all optional, defaults shown):

    * ``gaussian_sigma`` (float, default 2.0): Gaussian noise standard deviation.
    * ``hot_pixel_density`` (float, default 0.001): Hot pixel density fraction.
    * ``cosmic_ray_probability`` (float, default 0.01): Per-frame probability
      that a cosmic-ray event is injected.

    Args:
        image: Input grayscale image of dtype ``uint8``.
        config: Noise configuration dictionary.
        rng: Optional NumPy random generator shared across all noise stages for
            reproducibility.  A fresh generator is created when *None*.

    Returns:
        New ``uint8`` image with all requested noise applied in order:
        Gaussian → hot pixels → (optional) cosmic ray.
    """
    _rng = rng if rng is not None else np.random.default_rng()

    sigma: float = float(config.get("gaussian_sigma", 2.0))
    density: float = float(config.get("hot_pixel_density", 0.001))
    cr_prob: float = float(config.get("cosmic_ray_probability", 0.01))

    result = add_gaussian_noise(image, sigma=sigma, rng=_rng)
    result = add_hot_pixels(result, density=density, rng=_rng)
    if _rng.random() < cr_prob:
        result = add_cosmic_ray(result, rng=_rng)
    return result
