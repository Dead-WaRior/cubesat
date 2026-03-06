"""Two-stage debris detector combining streak and object detectors."""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from vision.object_detector import ObjectDetector
from vision.streak_detector import StreakDetector

logger = logging.getLogger(__name__)


class DebrisDetector:
    """Merge detections from :class:`StreakDetector` and :class:`ObjectDetector`.

    Detection proceeds in two parallel stages:

    1. **Streak stage** – Canny + HoughLinesP for fast-moving objects.
    2. **Object stage** – YOLOv8 (or blob fallback) for point sources.

    Overlapping detections (IoU > 0.3) from both stages are merged into a
    single detection with a boosted confidence score.

    Attributes:
        streak_detector: Streak-detection stage.
        object_detector: Object-detection stage.
        confidence_threshold: Minimum confidence to keep a detection.
    """

    def __init__(
        self,
        use_yolo: bool = False,
        confidence_threshold: float = 0.3,
    ) -> None:
        """Initialise both detection stages.

        Args:
            use_yolo: If *True*, attempt to load the default YOLOv8 model.
                      Falls back to blob detection automatically.
            confidence_threshold: Detections below this score are dropped.
        """
        self.confidence_threshold = confidence_threshold
        self.streak_detector = StreakDetector()
        model_path = "runs/detect/debris_detector/weights/best.pt" if use_yolo else None
        self.object_detector = ObjectDetector(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> List[dict]:
        """Run both detectors and return a merged, deduplicated detection list.

        Args:
            image: Preprocessed input image (uint8, grayscale or BGR).

        Returns:
            List of detection dicts (``x``, ``y``, ``w``, ``h``,
            ``confidence``, ``detection_type``) filtered by
            :attr:`confidence_threshold`.
        """
        streak_dets = self.streak_detector.detect(image)
        object_dets = self.object_detector.detect(image)

        merged = self._merge_detections(streak_dets, object_dets)
        filtered = [d for d in merged if d["confidence"] >= self.confidence_threshold]

        logger.debug(
            "DebrisDetector: %d streaks + %d objects → %d merged → %d after threshold",
            len(streak_dets),
            len(object_dets),
            len(merged),
            len(filtered),
        )
        return filtered

    # ------------------------------------------------------------------
    # Merging helpers
    # ------------------------------------------------------------------

    def _merge_detections(
        self, dets1: List[dict], dets2: List[dict]
    ) -> List[dict]:
        """Merge and deduplicate two detection lists.

        Pairs of detections across the two lists that overlap (IoU ≥ 0.3) are
        collapsed into one entry whose confidence is the mean of both scores
        plus a 0.1 co-detection bonus (capped at 1.0).

        Unmatched detections from either list are included as-is.

        Args:
            dets1: Detections from the first detector (streak).
            dets2: Detections from the second detector (object).

        Returns:
            Merged list of detection dicts.
        """
        if not dets1:
            return list(dets2)
        if not dets2:
            return list(dets1)

        used2 = set()
        result: List[dict] = []

        for d1 in dets1:
            best_iou = 0.0
            best_j = -1
            for j, d2 in enumerate(dets2):
                if j in used2:
                    continue
                iou = self._compute_iou(d1, d2)
                if iou > best_iou:
                    best_iou = iou
                    best_j = j

            if best_iou >= 0.3 and best_j >= 0:
                d2 = dets2[best_j]
                used2.add(best_j)
                merged_conf = min((d1["confidence"] + d2["confidence"]) / 2.0 + 0.1, 1.0)
                # Use the bounding box from whichever detection is larger
                area1 = d1["w"] * d1["h"]
                area2 = d2["w"] * d2["h"]
                base = d1 if area1 >= area2 else d2
                result.append(
                    {
                        "x": base["x"],
                        "y": base["y"],
                        "w": base["w"],
                        "h": base["h"],
                        "confidence": merged_conf,
                        "detection_type": d1["detection_type"],
                    }
                )
            else:
                result.append(d1)

        # Append unmatched object detections
        for j, d2 in enumerate(dets2):
            if j not in used2:
                result.append(d2)

        return result

    def _compute_iou(self, box1: dict, box2: dict) -> float:
        """Compute Intersection-over-Union for two bounding-box dicts.

        Each dict must contain ``x``, ``y``, ``w``, ``h`` keys (pixel coords).

        Args:
            box1: First bounding box.
            box2: Second bounding box.

        Returns:
            IoU value in [0, 1].
        """
        x1_1, y1_1 = box1["x"], box1["y"]
        x2_1, y2_1 = x1_1 + box1["w"], y1_1 + box1["h"]

        x1_2, y1_2 = box2["x"], box2["y"]
        x2_2, y2_2 = x1_2 + box2["w"], y1_2 + box2["h"]

        inter_x1 = max(x1_1, x1_2)
        inter_y1 = max(y1_1, y1_2)
        inter_x2 = min(x2_1, x2_2)
        inter_y2 = min(y2_1, y2_2)

        inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = area1 + area2 - inter_area

        return inter_area / (union_area + 1e-6)
