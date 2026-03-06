"""Object detector wrapping YOLOv8 with a blob-detection fallback."""

from __future__ import annotations

import logging
from typing import List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_BLOB_CONFIDENCE: float = 0.5  # Fallback confidence when SimpleBlobDetector response is zero


class ObjectDetector:
    """Detect point-source debris objects using YOLOv8 or blob detection.

    On construction the class attempts to load a YOLOv8 model.  If the
    ``ultralytics`` package is unavailable or *model_path* points to a
    missing file, it silently falls back to OpenCV's
    :class:`~cv2.SimpleBlobDetector` so the pipeline remains functional
    without a trained model.

    Attributes:
        confidence_threshold: Minimum confidence score to accept a detection.
        _yolo_model: Loaded YOLO model instance, or *None* if unavailable.
        _use_yolo: Whether YOLO inference is active.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.3,
    ) -> None:
        """Initialise the detector.

        Args:
            model_path: Path to a YOLOv8 ``.pt`` weights file.  If *None* or
                        the file cannot be loaded, blob detection is used.
            confidence_threshold: Detections below this score are discarded.
        """
        self.confidence_threshold = confidence_threshold
        self._yolo_model = None
        self._use_yolo = False

        if model_path is not None:
            self._try_load_yolo(model_path)

        if not self._use_yolo:
            logger.info(
                "ObjectDetector: YOLO unavailable – using blob detection fallback"
            )
            self._blob_detector = self._build_blob_detector()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> List[dict]:
        """Detect objects in *image*.

        Args:
            image: Input image (uint8, grayscale or BGR).

        Returns:
            List of detection dictionaries with keys:

            * ``x`` – left edge of bounding box (pixels).
            * ``y`` – top edge of bounding box (pixels).
            * ``w`` – bounding-box width (pixels).
            * ``h`` – bounding-box height (pixels).
            * ``confidence`` – detector confidence score in [0, 1].
            * ``detection_type`` – ``"point"`` (YOLO class-0) or ``"blob"``.
        """
        if self._use_yolo:
            return self._yolo_detect(image)
        return self._blob_detection_fallback(image)

    # ------------------------------------------------------------------
    # YOLO inference
    # ------------------------------------------------------------------

    def _try_load_yolo(self, model_path: str) -> None:
        """Attempt to load a YOLOv8 model, setting *_use_yolo* on success."""
        try:
            from ultralytics import YOLO  # type: ignore

            self._yolo_model = YOLO(model_path)
            self._use_yolo = True
            logger.info("ObjectDetector: loaded YOLO model from %s", model_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ObjectDetector: could not load YOLO model (%s) – falling back to blob detection",
                exc,
            )

    def _yolo_detect(self, image: np.ndarray) -> List[dict]:
        """Run YOLOv8 inference and convert results to detection dicts."""
        results = self._yolo_model.predict(
            image, conf=self.confidence_threshold, verbose=False
        )
        detections: List[dict] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                detections.append(
                    {
                        "x": float(x1),
                        "y": float(y1),
                        "w": float(x2 - x1),
                        "h": float(y2 - y1),
                        "confidence": conf,
                        "detection_type": "point",
                    }
                )
        logger.debug("YOLO detected %d objects", len(detections))
        return detections

    # ------------------------------------------------------------------
    # Blob detection fallback
    # ------------------------------------------------------------------

    def _blob_detection_fallback(self, image: np.ndarray) -> List[dict]:
        """Detect bright point sources using OpenCV's SimpleBlobDetector.

        Args:
            image: Input image (uint8, grayscale or BGR).

        Returns:
            Detection dictionaries with ``detection_type="blob"``.
        """
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        keypoints = self._blob_detector.detect(gray)

        detections: List[dict] = []
        for kp in keypoints:
            radius = max(kp.size / 2.0, 1.0)
            detections.append(
                {
                    "x": float(kp.pt[0] - radius),
                    "y": float(kp.pt[1] - radius),
                    "w": float(radius * 2),
                    "h": float(radius * 2),
                    "confidence": min(kp.response / 255.0 if kp.response > 0 else _DEFAULT_BLOB_CONFIDENCE, 1.0),
                    "detection_type": "blob",
                }
            )

        logger.debug("BlobDetector found %d blobs", len(detections))
        return detections

    @staticmethod
    def _build_blob_detector() -> cv2.SimpleBlobDetector:
        """Build and return a configured :class:`~cv2.SimpleBlobDetector`."""
        params = cv2.SimpleBlobDetector_Params()
        params.filterByColor = True
        params.blobColor = 255  # Detect bright blobs
        params.filterByArea = True
        params.minArea = 4
        params.maxArea = 2000
        params.filterByCircularity = False
        params.filterByConvexity = False
        params.filterByInertia = False
        params.minThreshold = 50
        params.maxThreshold = 255
        params.thresholdStep = 10
        return cv2.SimpleBlobDetector_create(params)
