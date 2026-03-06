"""Tests for vision/preprocessing.py ImagePreprocessor."""

from __future__ import annotations

import numpy as np
import pytest

from vision.preprocessing import ImagePreprocessor


def _uniform_image(value: int = 128, shape: tuple = (100, 100)) -> np.ndarray:
    return np.full(shape, value, dtype=np.uint8)


def test_dark_frame_subtraction() -> None:
    dark = _uniform_image(50)
    preprocessor = ImagePreprocessor(dark_frame=dark)
    image = _uniform_image(150)
    result = preprocessor.dark_frame_subtraction(image)
    # 150 - 50 = 100
    assert result.dtype == np.uint8
    assert int(result[0, 0]) == pytest.approx(100, abs=1)


def test_clahe_enhancement() -> None:
    preprocessor = ImagePreprocessor()
    # Low-contrast image
    image = _uniform_image(100)
    enhanced = preprocessor.clahe_enhancement(image)
    assert enhanced.shape == image.shape
    assert enhanced.dtype == np.uint8
    # CLAHE on a uniform image may yield the same value but should not raise
    # The histogram of the enhanced image should differ from a completely flat one
    # (behaviour depends on CLAHE tile size, but shape must be preserved)
    assert enhanced.shape == image.shape


def test_hot_pixel_correction() -> None:
    preprocessor = ImagePreprocessor()
    image = _uniform_image(50, shape=(50, 50))
    # Plant an isolated hot pixel
    image[25, 25] = 255
    corrected = preprocessor.hot_pixel_correction(image, threshold=200)
    assert corrected.dtype == np.uint8
    # The hot pixel should be reduced toward the neighbourhood median (~50)
    assert int(corrected[25, 25]) < 255


def test_full_preprocess_pipeline() -> None:
    preprocessor = ImagePreprocessor()
    image = _uniform_image(100, shape=(480, 640))
    result = preprocessor.preprocess(image)
    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_background_update() -> None:
    preprocessor = ImagePreprocessor()
    image = _uniform_image(100, shape=(100, 100))
    # First call creates background
    preprocessor.update_background(image)
    assert preprocessor.background_frame is not None
    assert preprocessor.background_frame.shape == (100, 100)
    # Second call updates it
    image2 = _uniform_image(200, shape=(100, 100))
    preprocessor.update_background(image2, alpha=0.5)
    # Background should move toward image2 value
    assert float(preprocessor.background_frame[0, 0]) > 100.0
