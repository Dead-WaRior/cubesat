"""End-to-end prediction pipeline: track → TCA → Pc → risk alert."""

from __future__ import annotations

from typing import Optional

import numpy as np

from prediction.coordinate_transform import CoordinateTransformer
from prediction.ukf_tracker import UKFTracker
from prediction.closest_approach import ClosestApproachCalculator
from prediction.collision_probability import CollisionProbabilityCalculator
from prediction.risk_assessor import RiskAssessor
from shared.schemas import RiskAlert, TelemetryPacket

# Default slant-range assumption when no independent range measurement is
# available.  1 km is a conservative close-approach starting assumption.
_DEFAULT_RANGE_KM: float = 1.0

# Default debris covariance – used when a track has no established UKF history.
_DEFAULT_DEBRIS_COV: np.ndarray = np.diag([1.0, 1.0, 1.0, 0.01, 0.01, 0.01])


class PredictionPipeline:
    """Orchestrates the full prediction chain for all active debris tracks.

    For each active track the pipeline:

    1. Converts the pixel-space detection centroid to an ECI position
       estimate using the current satellite telemetry.
    2. Updates (or initialises) the per-track :class:`~prediction.ukf_tracker.UKFTracker`.
    3. Computes the Time of Closest Approach (TCA) and miss distance.
    4. Estimates the probability of collision (Pc).
    5. Runs risk assessment and collects any resulting alerts.
    """

    def __init__(self) -> None:
        self._transformer = CoordinateTransformer()
        self._trackers: dict[int, UKFTracker] = {}
        self._tca_calculator = ClosestApproachCalculator()
        self._pc_calculator = CollisionProbabilityCalculator()
        self._risk_assessor = RiskAssessor()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_tracks(
        self,
        active_tracks: list[dict],
        telemetry: TelemetryPacket,
    ) -> list[RiskAlert]:
        """Process a batch of active tracks and return any triggered risk alerts.

        Each element of *active_tracks* must be a ``dict`` with at least:

        * ``track_id`` (*int*) – unique track identifier.
        * ``bbox`` (*dict*) – bounding box with keys ``x``, ``y``, ``w``, ``h``
          (pixel coordinates).
        * Optionally ``range_km`` (*float*) – slant range estimate.

        Args:
            active_tracks: List of track descriptor dicts from the vision layer.
            telemetry: Current satellite telemetry packet.

        Returns:
            List of :class:`~shared.schemas.RiskAlert` objects, one per track
            that exceeded at least one risk threshold.
        """
        sat_pos = telemetry.satellite_position
        sat_vel = telemetry.velocity

        sat_state = np.array([
            sat_pos["x"], sat_pos["y"], sat_pos["z"],
            sat_vel["vx"], sat_vel["vy"], sat_vel["vz"],
        ])

        alerts: list[RiskAlert] = []

        for track in active_tracks:
            track_id: int = int(track["track_id"])
            bbox: dict = track["bbox"]
            range_km: float = float(track.get("range_km", _DEFAULT_RANGE_KM))

            # Pixel centroid from bounding box
            px = bbox["x"] + bbox["w"] / 2.0
            py = bbox["y"] + bbox["h"] / 2.0

            # Convert pixel → ECI position measurement
            az, el = self._transformer.pixel_to_angular(px, py)
            meas_pos = self._transformer.angular_to_eci(az, el, range_km, sat_pos)

            # Initialise or update UKF tracker
            if track_id not in self._trackers:
                initial_vel = np.array([
                    sat_vel["vx"] * 1.001,
                    sat_vel["vy"] * 1.001,
                    sat_vel["vz"] * 1.001,
                ])
                initial_state = np.concatenate([meas_pos, initial_vel])
                self._trackers[track_id] = UKFTracker(
                    track_id=track_id,
                    initial_state=initial_state,
                )
            else:
                self._trackers[track_id].predict()
                self._trackers[track_id].update(meas_pos)

            tracker = self._trackers[track_id]
            debris_state = tracker.get_state()
            debris_cov = tracker.get_covariance()

            # TCA computation
            tca_s, miss_km, _, _ = self._tca_calculator.compute_tca(
                sat_state, debris_state
            )

            # Collision probability
            sat_cov = _DEFAULT_DEBRIS_COV.copy()
            combined_cov = self._pc_calculator.combine_covariances(sat_cov, debris_cov)
            pc = self._pc_calculator.compute_pc(miss_km, combined_cov)

            # Risk assessment
            alert = self._risk_assessor.assess(track_id, pc, miss_km, tca_s)
            if alert is not None:
                alerts.append(alert)

        return alerts

    def get_track_prediction(
        self,
        track_id: int,
        seconds_forward: float = 600.0,
    ) -> Optional[np.ndarray]:
        """Return the predicted state for a tracked object at a future time.

        Args:
            track_id: Identifier of the track to predict.
            seconds_forward: Number of seconds ahead to propagate.

        Returns:
            Predicted state vector ``[x, y, z, vx, vy, vz]``, shape ``(6,)``,
            or ``None`` if the track is not known to this pipeline instance.
        """
        tracker = self._trackers.get(track_id)
        if tracker is None:
            return None
        predicted_state, _ = tracker.propagate_forward(seconds_forward)
        return predicted_state
