"""SORT tracker with Kalman filter for multi-object tracking."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from filterpy.kalman import KalmanFilter

logger = logging.getLogger(__name__)


class KalmanBoxTracker:
    """Single object tracker using a constant-velocity Kalman filter.

    State vector: ``[x, y, w, h, vx, vy, vw, vh]``

    where ``(x, y)`` is the top-left corner and ``(w, h)`` are the
    bounding-box dimensions, all in pixels.

    Attributes:
        id: Unique tracker identifier (auto-incremented class counter).
        kf: Underlying :class:`~filterpy.kalman.KalmanFilter`.
        history: List of recent predicted states (up to 100 entries).
        hits: Total number of successful updates.
        no_loss: Consecutive frames since the last missed detection; reset to zero on each update.
        time_since_update: Frames elapsed since the last :meth:`update` call.
        confidence: Confidence of the most recent associated detection.
    """

    count: int = 0

    def __init__(self, bbox: List[float]) -> None:
        """Initialise tracker with an initial bounding box.

        Args:
            bbox: Initial bounding box as ``[x, y, w, h]`` (pixels).
        """
        # State: [x, y, w, h, vx, vy, vw, vh]
        self.kf = KalmanFilter(dim_x=8, dim_z=4)
        self.kf.F = np.array(
            [
                [1, 0, 0, 0, 1, 0, 0, 0],
                [0, 1, 0, 0, 0, 1, 0, 0],
                [0, 0, 1, 0, 0, 0, 1, 0],
                [0, 0, 0, 1, 0, 0, 0, 1],
                [0, 0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 0, 0, 1],
            ],
            dtype=float,
        )
        self.kf.H = np.array(
            [
                [1, 0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 1, 0, 0, 0, 0],
            ],
            dtype=float,
        )
        self.kf.R *= 10.0
        self.kf.P[4:, 4:] *= 1000.0
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01
        self.kf.x[:4] = np.array(bbox, dtype=float).reshape(4, 1)

        KalmanBoxTracker.count += 1
        self.id: int = KalmanBoxTracker.count
        self.history: List[List[float]] = []
        self.hits: int = 0
        self.no_loss: int = 0  # consecutive frames since last missed detection
        self.time_since_update: int = 0
        self.confidence: float = 0.0

    def update(self, bbox: List[float], confidence: float = 1.0) -> None:
        """Incorporate a new detection measurement.

        Args:
            bbox: Measured bounding box ``[x, y, w, h]`` (pixels).
            confidence: Detection confidence score in [0, 1].
        """
        self.time_since_update = 0
        self.hits += 1
        self.no_loss = 0
        self.confidence = confidence
        self.kf.update(np.array(bbox, dtype=float).reshape(4, 1))

    def predict(self) -> List[float]:
        """Advance the Kalman filter by one time step and return predicted state.

        Returns:
            Predicted bounding box ``[x, y, w, h]`` (pixels).
        """
        self.kf.predict()
        self.time_since_update += 1
        state = self.kf.x[:4].flatten().tolist()
        self.history.append(state)
        if len(self.history) > 100:
            self.history.pop(0)
        return state

    def get_state(self) -> List[float]:
        """Return the current Kalman state estimate as ``[x, y, w, h]``.

        Returns:
            Current bounding box estimate (pixels).
        """
        return self.kf.x[:4].flatten().tolist()


class SORTTracker:
    """SORT (Simple Online and Realtime Tracking) multi-object tracker.

    Maintains a set of :class:`KalmanBoxTracker` instances, associates
    incoming detections with existing tracks using an IoU-based greedy
    matching algorithm, and removes stale tracks after :attr:`max_age`
    frames without an update.

    Attributes:
        max_age: Frames a track can go unmatched before removal.
        min_hits: Minimum hits before a track is reported in output.
        iou_threshold: Minimum IoU to consider a detection-track pair matched.
        trackers: Active :class:`KalmanBoxTracker` instances.
        frame_count: Total frames processed since initialisation.
    """

    def __init__(
        self,
        max_age: int = 5,
        min_hits: int = 4,
        iou_threshold: float = 0.3,
    ) -> None:
        """Initialise the SORT tracker.

        Args:
            max_age: Maximum frames without update before a track is removed.
            min_hits: Minimum confirmed hits before a track is included in
                      the returned results.
            iou_threshold: IoU threshold for matching detections to tracks.
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers: List[KalmanBoxTracker] = []
        self.frame_count: int = 0

    def update(self, detections: List[Dict]) -> List[Dict]:
        """Update the tracker with new detections and return active tracks.

        Args:
            detections: List of detection dicts with keys ``x``, ``y``, ``w``,
                        ``h``, and optionally ``confidence``.

        Returns:
            List of active track dicts with keys ``track_id``, ``x``, ``y``,
            ``w``, ``h``, ``confidence``, ``age_in_frames``, and
            ``time_since_update``.
        """
        self.frame_count += 1

        if detections:
            dets = np.array(
                [
                    [d["x"], d["y"], d["w"], d["h"], d.get("confidence", 1.0)]
                    for d in detections
                ]
            )
        else:
            dets = np.empty((0, 5))

        # Predict next state for all existing trackers
        predicted_boxes: List[List[float]] = []
        to_del: List[int] = []
        for i, trk in enumerate(self.trackers):
            pos = trk.predict()
            if any(np.isnan(pos)):
                to_del.append(i)
            else:
                predicted_boxes.append(pos)
        for i in reversed(to_del):
            self.trackers.pop(i)

        matched, unmatched_dets, _ = self._associate(dets, predicted_boxes)

        # Update matched trackers with their associated detections
        for m in matched:
            self.trackers[m[1]].update(
                dets[m[0], :4].tolist(), float(dets[m[0], 4])
            )

        # Spawn new trackers for unmatched detections
        for i in unmatched_dets:
            self.trackers.append(KalmanBoxTracker(dets[i, :4].tolist()))

        # Prune stale trackers
        self.trackers = [
            t for t in self.trackers if t.time_since_update <= self.max_age
        ]

        results: List[Dict] = []
        for trk in self.trackers:
            if trk.hits >= self.min_hits or self.frame_count <= self.min_hits:
                state = trk.get_state()
                results.append(
                    {
                        "track_id": trk.id,
                        "x": state[0],
                        "y": state[1],
                        "w": state[2],
                        "h": state[3],
                        "confidence": trk.confidence,
                        "age_in_frames": trk.hits,
                        "time_since_update": trk.time_since_update,
                    }
                )
        return results

    # ------------------------------------------------------------------
    # Association
    # ------------------------------------------------------------------

    def _associate(
        self,
        detections: np.ndarray,
        predicted: List[List[float]],
    ) -> Tuple[List[List[int]], List[int], List[int]]:
        """Associate detections with predicted tracker positions.

        Uses a greedy algorithm that processes detection-prediction pairs in
        descending IoU order.

        Args:
            detections: Array of shape ``(N, 5)`` with columns
                        ``[x, y, w, h, conf]``.
            predicted: List of ``[x, y, w, h]`` predicted bounding boxes.

        Returns:
            Tuple of ``(matched, unmatched_dets, unmatched_preds)`` where
            *matched* is a list of ``[det_idx, pred_idx]`` pairs and the
            others are index lists.
        """
        if len(predicted) == 0:
            return [], list(range(len(detections))), []
        if len(detections) == 0:
            return [], [], list(range(len(predicted)))

        iou_matrix = np.zeros((len(detections), len(predicted)), dtype=float)
        for d in range(len(detections)):
            for p in range(len(predicted)):
                iou_matrix[d, p] = self._iou(detections[d, :4], predicted[p])

        matched_indices: List[List[int]] = []
        used_dets: set = set()
        used_preds: set = set()

        flat_indices = np.argsort(-iou_matrix.flatten())
        for idx in flat_indices:
            d = int(idx) // len(predicted)
            p = int(idx) % len(predicted)
            if d in used_dets or p in used_preds:
                continue
            if iou_matrix[d, p] < self.iou_threshold:
                break
            matched_indices.append([d, p])
            used_dets.add(d)
            used_preds.add(p)

        unmatched_dets = [d for d in range(len(detections)) if d not in used_dets]
        unmatched_preds = [p for p in range(len(predicted)) if p not in used_preds]

        return matched_indices, unmatched_dets, unmatched_preds

    def _iou(self, box1: np.ndarray, box2: List[float]) -> float:
        """Compute Intersection-over-Union between two ``[x, y, w, h]`` boxes.

        Args:
            box1: First bounding box as a 1-D array ``[x, y, w, h]``.
            box2: Second bounding box as a list ``[x, y, w, h]``.

        Returns:
            IoU value in [0, 1].
        """
        x1_1, y1_1 = float(box1[0]), float(box1[1])
        x2_1, y2_1 = x1_1 + float(box1[2]), y1_1 + float(box1[3])
        x1_2, y1_2 = float(box2[0]), float(box2[1])
        x2_2, y2_2 = x1_2 + float(box2[2]), y1_2 + float(box2[3])

        inter_x1 = max(x1_1, x1_2)
        inter_y1 = max(y1_1, y1_2)
        inter_x2 = min(x2_1, x2_2)
        inter_y2 = min(y2_1, y2_2)

        inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = area1 + area2 - inter_area

        return inter_area / (union_area + 1e-6)
