"""End-to-end prediction pipeline: track → TCA → Pc → risk alert."""

from __future__ import annotations

from typing import Optional

import numpy as np

from prediction.coordinate_transform import CoordinateTransformer
from prediction.ukf_tracker import UKFTracker
from prediction.closest_approach import ClosestApproachCalculator
from prediction.collision_probability import CollisionProbabilityCalculator
from prediction.risk_assessor import RiskAssessor
from prediction.maneuver_planner import ManeuverPlanner
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
        self._maneuver_planner = ManeuverPlanner()

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
                # Try to plan avoidance if risk is high
                if tca_s < 3600: # plan if TCA within 1 hour
                    maneuver = self._maneuver_planner.plan_avoidance(
                        sat_state, debris_state, tca_s
                    )
                    if maneuver:
                        alert.recommended_action += f" | {maneuver['direction'].upper()} burn: {maneuver['delta_v_ms']} m/s"
                alerts.append(alert)

        return alerts

    def get_track_prediction(
        self,
        track_id: int,
        seconds_forward: float = 600.0,
    ) -> Optional[np.ndarray]:
        """Return the predicted state for a tracked object at a future time."""
        tracker = self._trackers.get(track_id)
        if tracker is None:
            return None
        predicted_state, _ = tracker.propagate_forward(seconds_forward)
        return predicted_state

    def get_prediction_path(
        self,
        track_id: int,
        duration: float = 300.0,
        steps: int = 10,
    ) -> Optional[list[dict[str, float]]]:
        """Return a series of predicted positions for a track identifier."""
        tracker = self._trackers.get(track_id)
        if tracker is None:
            return None
        
        path = []
        dt = duration / (steps - 1)
        for i in range(steps):
            t = i * dt
            state, _ = tracker.propagate_forward(t)
            path.append({"x": float(state[0]), "y": float(state[1]), "z": float(state[2])})
        return path

    def get_sat_prediction_path(
        self,
        sat_state: np.ndarray,
        duration: float = 300.0,
        steps: int = 10,
    ) -> list[dict[str, float]]:
        """Return a series of predicted positions for the satellite itself."""
        from prediction.orbital_dynamics import propagate_state
        path = []
        dt = duration / (steps - 1)
        for i in range(steps):
            t = i * dt
            # Propagate from original state to current offset
            state = propagate_state(sat_state, t)
            path.append({"x": float(state[0]), "y": float(state[1]), "z": float(state[2])})
        return path
