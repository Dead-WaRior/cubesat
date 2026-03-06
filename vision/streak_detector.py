"""Streak detector for fast-moving debris that leaves linear trails."""

from __future__ import annotations

import logging
import math
from typing import List

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class StreakDetector:
    """Detect linear debris streaks using Canny edges and Hough line transform.

    Attributes:
        canny_low: Lower hysteresis threshold for Canny edge detection.
        canny_high: Upper hysteresis threshold for Canny edge detection.
        hough_threshold: Accumulator threshold for :func:`cv2.HoughLinesP`.
        min_line_length: Minimum accepted streak length in pixels.
        max_line_gap: Maximum gap between collinear segments to bridge.
    """

    def __init__(
        self,
        canny_low: int = 50,
        canny_high: int = 150,
        hough_threshold: int = 30,
        min_line_length: int = 20,
        max_line_gap: int = 10,
    ) -> None:
        """Initialise streak detector with Canny and Hough parameters.

        Args:
            canny_low: Lower Canny hysteresis threshold.
            canny_high: Upper Canny hysteresis threshold.
            hough_threshold: Minimum Hough accumulator votes to accept a line.
            min_line_length: Minimum line length (pixels) to report.
            max_line_gap: Maximum gap (pixels) to bridge between line segments.
        """
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.hough_threshold = hough_threshold
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap

    def detect(self, image: np.ndarray) -> List[dict]:
        """Detect streaks in *image* and return bounding-box detections.

        Processing steps:

        1. Convert to grayscale (if colour input).
        2. Apply Canny edge detection.
        3. Apply Probabilistic Hough transform to find line segments.
        4. Convert each accepted segment to an axis-aligned bounding box.
        5. Filter segments shorter than :attr:`min_line_length`.

        Args:
            image: Input image (uint8, grayscale or BGR).

        Returns:
            List of detection dictionaries with keys:

            * ``x`` – left edge of bounding box (pixels).
            * ``y`` – top edge of bounding box (pixels).
            * ``w`` – bounding-box width (pixels).
            * ``h`` – bounding-box height (pixels).
            * ``confidence`` – normalised line length score in [0, 1].
            * ``detection_type`` – always ``"streak"``.
        """
        gray = self._to_gray(image)
        edges = cv2.Canny(gray, self.canny_low, self.canny_high)

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap,
        )

        if lines is None:
            return []

        detections: List[dict] = []
        max_dim = max(image.shape[0], image.shape[1])

        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = math.hypot(x2 - x1, y2 - y1)

            if length < self.min_line_length:
                continue

            bx = int(min(x1, x2))
            by = int(min(y1, y2))
            bw = max(int(abs(x2 - x1)), 1)
            bh = max(int(abs(y2 - y1)), 1)

            # Confidence: normalised line length capped at 1.0
            confidence = min(length / max_dim, 1.0)

            detections.append(
                {
                    "x": float(bx),
                    "y": float(by),
                    "w": float(bw),
                    "h": float(bh),
                    "confidence": confidence,
                    "detection_type": "streak",
                }
            )

        logger.debug("StreakDetector found %d streaks", len(detections))
        return detections

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_gray(image: np.ndarray) -> np.ndarray:
        """Return a grayscale view of *image* without copying if already gray."""
        if image.ndim == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
