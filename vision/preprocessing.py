"""Image preprocessing for space-based debris detection."""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Applies a configurable preprocessing pipeline to raw sensor frames.

    Steps applied by :meth:`preprocess` in order:

    1. Dark-frame subtraction
    2. Background subtraction (running average)
    3. CLAHE contrast enhancement
    4. Hot-pixel correction

    Attributes:
        dark_frame: Optional dark calibration frame used for bias subtraction.
        background_frame: Running-average background model (float32).
    """

    def __init__(
        self,
        dark_frame: Optional[np.ndarray] = None,
        background_frame: Optional[np.ndarray] = None,
    ) -> None:
        """Initialise the preprocessor with optional calibration frames.

        Args:
            dark_frame: Dark calibration frame (same shape as input images).
                        If *None*, dark-frame subtraction is a no-op.
            background_frame: Initial background model (float32, same shape as
                              input images).  If *None*, it is lazily created
                              from the first processed frame.
        """
        self.dark_frame: Optional[np.ndarray] = (
            dark_frame.astype(np.float32) if dark_frame is not None else None
        )
        self.background_frame: Optional[np.ndarray] = (
            background_frame.astype(np.float32) if background_frame is not None else None
        )
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    # ------------------------------------------------------------------
    # Individual processing steps
    # ------------------------------------------------------------------

    def dark_frame_subtraction(self, image: np.ndarray) -> np.ndarray:
        """Subtract the dark calibration frame from *image*.

        Args:
            image: Input image (uint8 or float32, grayscale or colour).

        Returns:
            Dark-corrected image clipped to [0, 255] as *uint8*.
        """
        img_f = image.astype(np.float32)
        dark = self.dark_frame if self.dark_frame is not None else np.zeros_like(img_f)
        corrected = np.clip(img_f - dark, 0, 255)
        return corrected.astype(np.uint8)

    def background_subtraction(self, image: np.ndarray) -> np.ndarray:
        """Subtract the running-average background from *image*.

        If no background model exists yet, the current frame is used to
        initialise it and the original image is returned unchanged.

        Args:
            image: Input image (uint8 or float32, grayscale or colour).

        Returns:
            Background-subtracted image clipped to [0, 255] as *uint8*.
        """
        img_f = image.astype(np.float32)
        if self.background_frame is None:
            self.background_frame = img_f.copy()
            return image.astype(np.uint8)
        subtracted = np.clip(img_f - self.background_frame, 0, 255)
        return subtracted.astype(np.uint8)

    def clahe_enhancement(self, image: np.ndarray) -> np.ndarray:
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalisation).

        For colour images each channel is processed independently.

        Args:
            image: Input image (uint8, grayscale or BGR).

        Returns:
            Contrast-enhanced image (uint8, same shape as input).
        """
        if image.ndim == 2:
            return self._clahe.apply(image)

        channels = cv2.split(image)
        enhanced = [self._clahe.apply(ch) for ch in channels]
        return cv2.merge(enhanced)

    def hot_pixel_correction(
        self, image: np.ndarray, threshold: int = 250
    ) -> np.ndarray:
        """Replace isolated hot pixels with the local 3×3 median.

        A pixel is considered *hot* if its value exceeds *threshold* and none
        of its 8-connected neighbours also exceed *threshold* (i.e., it is
        isolated).

        Args:
            image: Input grayscale or colour image (uint8).
            threshold: Pixel value above which a pixel is a hot-pixel candidate.

        Returns:
            Corrected image (uint8, same shape as input).
        """
        result = image.copy()
        if image.ndim == 2:
            result = self._correct_hot_pixels_single(result, threshold)
        else:
            for c in range(image.shape[2]):
                result[:, :, c] = self._correct_hot_pixels_single(
                    image[:, :, c], threshold
                )
        return result

    def _correct_hot_pixels_single(
        self, channel: np.ndarray, threshold: int
    ) -> np.ndarray:
        """Hot-pixel correction for a single 2-D channel."""
        hot_mask = channel > threshold
        # Isolated hot pixels: hot but no non-self hot neighbours
        kernel = np.ones((3, 3), np.uint8)
        neighbour_count = cv2.filter2D(
            hot_mask.astype(np.float32), -1, kernel.astype(np.float32)
        )
        isolated = hot_mask & (neighbour_count <= 1)

        if not np.any(isolated):
            return channel

        median_filtered = cv2.medianBlur(channel, 3)
        result = channel.copy()
        result[isolated] = median_filtered[isolated]
        return result

    # ------------------------------------------------------------------
    # Pipeline entry-points
    # ------------------------------------------------------------------

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Apply the full preprocessing pipeline to *image*.

        Steps applied in order:

        1. Dark-frame subtraction
        2. Background subtraction
        3. CLAHE enhancement
        4. Hot-pixel correction

        The background model is updated *after* step 2 using the
        dark-corrected (but not background-subtracted) image so that slow
        scene changes are tracked without leaking subtracted residuals.

        Args:
            image: Raw input image (uint8, grayscale or BGR).

        Returns:
            Preprocessed image (uint8, same shape as input).
        """
        dark_corrected = self.dark_frame_subtraction(image)
        bg_subtracted = self.background_subtraction(dark_corrected)
        self.update_background(dark_corrected)
        enhanced = self.clahe_enhancement(bg_subtracted)
        corrected = self.hot_pixel_correction(enhanced)
        return corrected

    def update_background(self, image: np.ndarray, alpha: float = 0.05) -> None:
        """Update the running-average background model.

        Uses an exponential moving average:
        ``background = (1 - alpha) * background + alpha * image``.

        Args:
            image: New frame to incorporate (uint8 or float32).
            alpha: Learning rate in (0, 1].  Smaller values give a slower,
                   more stable background estimate.
        """
        img_f = image.astype(np.float32)
        if self.background_frame is None:
            self.background_frame = img_f.copy()
        else:
            cv2.accumulateWeighted(img_f, self.background_frame, alpha)
