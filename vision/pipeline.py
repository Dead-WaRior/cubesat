"""End-to-end vision pipeline: preprocessing → detection → tracking."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Tuple

import cv2
import numpy as np

from shared.schemas import DetectionEvent, DetectionType
from vision.detector import DebrisDetector
from vision.preprocessing import ImagePreprocessor
from vision.sort_tracker import SORTTracker

logger = logging.getLogger(__name__)


class VisionPipeline:
    """Orchestrate the full vision stack for a single camera input stream.

    Processing order per frame:

    1. **Preprocessing** – dark-frame subtraction, background subtraction,
       CLAHE enhancement, hot-pixel correction.
    2. **Detection** – two-stage detector (streak + object/blob).
    3. **Tracking** – SORT multi-object tracker with Kalman filtering.
    4. **Schema conversion** – active tracks → :class:`~shared.schemas.DetectionEvent`.

    Attributes:
        preprocessor: :class:`~vision.preprocessing.ImagePreprocessor` instance.
        detector: :class:`~vision.detector.DebrisDetector` instance.
        tracker: :class:`~vision.sort_tracker.SORTTracker` instance.
    """

    def __init__(self, use_yolo: bool = False) -> None:
        """Initialise the pipeline.

        Args:
            use_yolo: If *True*, the detector will attempt to load a YOLOv8
                      model.  Falls back to blob detection automatically.
        """
        self.preprocessor = ImagePreprocessor()
        self.detector = DebrisDetector(use_yolo=use_yolo)
        self.tracker = SORTTracker()

    # ------------------------------------------------------------------
    # Frame processing
    # ------------------------------------------------------------------

    def process_frame(
        self,
        image: np.ndarray,
        frame_id: str,
        timestamp: datetime,
    ) -> Tuple[List[DetectionEvent], List[dict]]:
        """Process a single frame end-to-end.

        Args:
            image: Raw camera frame (uint8, grayscale or BGR).
            frame_id: Unique identifier for this frame (used in output events).
            timestamp: UTC timestamp of frame capture.

        Returns:
            A 2-tuple of:

            * ``detection_events`` – list of :class:`~shared.schemas.DetectionEvent`
              objects corresponding to active, confirmed tracks.
            * ``active_tracks`` – raw tracker output dicts (``track_id``,
              ``x``, ``y``, ``w``, ``h``, ``confidence``, ``age_in_frames``,
              ``time_since_update``).
        """
        preprocessed = self.preprocessor.preprocess(image)
        detections = self.detector.detect(preprocessed)
        active_tracks = self.tracker.update(detections)

        detection_events = [
            self._track_to_event(track, frame_id, timestamp)
            for track in active_tracks
        ]

        logger.debug(
            "frame=%s detections=%d tracks=%d events=%d",
            frame_id,
            len(detections),
            len(active_tracks),
            len(detection_events),
        )
        return detection_events, active_tracks

    # ------------------------------------------------------------------
    # Annotation
    # ------------------------------------------------------------------

    def annotate_frame(
        self, image: np.ndarray, tracks: List[dict]
    ) -> np.ndarray:
        """Draw bounding boxes and track IDs on a copy of *image*.

        Bounding-box colour encodes confidence:

        * **Green** (confidence ≥ 0.6)
        * **Yellow** (0.3 ≤ confidence < 0.6)
        * **Red** (confidence < 0.3)

        Args:
            image: Source image (uint8, grayscale or BGR).
            tracks: Active track dicts as returned by :meth:`process_frame`.

        Returns:
            Annotated BGR image (uint8).
        """
        # Ensure BGR for colour drawing
        if image.ndim == 2:
            annotated = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            annotated = image.copy()

        for track in tracks:
            x = int(track["x"])
            y = int(track["y"])
            w = int(track["w"])
            h = int(track["h"])
            track_id = track["track_id"]
            conf = track.get("confidence", 0.0)

            color = self._confidence_color(conf)

            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)

            label = f"#{track_id} {conf:.2f}"
            label_y = max(y - 6, 12)
            cv2.putText(
                annotated,
                label,
                (x, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA,
            )

        return annotated

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _confidence_color(confidence: float) -> Tuple[int, int, int]:
        """Map a confidence score to a BGR annotation colour.

        Args:
            confidence: Score in [0, 1].

        Returns:
            BGR colour tuple.
        """
        if confidence >= 0.6:
            return (0, 200, 0)   # Green
        if confidence >= 0.3:
            return (0, 200, 200)  # Yellow
        return (0, 0, 200)       # Red

    @staticmethod
    def _track_to_event(
        track: dict, frame_id: str, timestamp: datetime
    ) -> DetectionEvent:
        """Convert a tracker output dict to a :class:`~shared.schemas.DetectionEvent`.

        Args:
            track: Track dict with ``track_id``, ``x``, ``y``, ``w``, ``h``,
                   ``confidence``.
            frame_id: Identifier of the source frame.
            timestamp: UTC capture timestamp.

        Returns:
            A populated :class:`~shared.schemas.DetectionEvent`.
        """
        return DetectionEvent(
            frame_id=frame_id,
            track_id=int(track["track_id"]),
            bbox={
                "x": float(track["x"]),
                "y": float(track["y"]),
                "w": float(track["w"]),
                "h": float(track["h"]),
            },
            confidence=float(track["confidence"]),
            detection_type=DetectionType.blob,
            timestamp=timestamp,
        )
