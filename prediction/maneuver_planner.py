"""Collision avoidance maneuver planner for CubeSats."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from prediction.orbital_dynamics import propagate_state
from prediction.closest_approach import ClosestApproachCalculator

class ManeuverPlanner:
    """Calculates impulsive maneuvers to avoid predicted collisions.
    
    The planner evaluates potential burns at a given lead time before TCA
    and recommends the one that achieves the target miss distance with
    minimal delta-v requirements.
    """

    def __init__(self, target_miss_km: float = 2.0) -> None:
        self.target_miss_km = target_miss_km
        self._tca_calculator = ClosestApproachCalculator()

    def plan_avoidance(
        self,
        sat_state: np.ndarray,
        debris_state: np.ndarray,
        tca_s: float,
        burn_lead_time_s: float = 600.0,
    ) -> Optional[dict]:
        """Plan an impulsive burn to avoid a conjunction.
        
        Args:
            sat_state: Current satellite state [x, y, z, vx, vy, vz].
            debris_state: Current debris state [x, y, z, vx, vy, vz].
            tca_s: Time to closest approach in seconds.
            burn_lead_time_s: How many seconds from now to perform the burn.
                Must be < tca_s.
        
        Returns:
            A dictionary describing the recommended maneuver, or None if
            no safe maneuver is found within limits.
        """
        if burn_lead_time_s >= tca_s:
            return None

        # 1. Propagate both to the burn time
        sat_at_burn = propagate_state(sat_state, burn_lead_time_s)
        debris_at_burn = propagate_state(debris_state, burn_lead_time_s)
        
        # 2. Define search space for delta-v (m/s)
        # We'll try prograde and retrograde burns first as they are most efficient
        # for changing the semi-major axis and thus the relative timing at TCA.
        v_unit = sat_at_burn[3:] / np.linalg.norm(sat_at_burn[3:])
        
        best_dv_mag = float('inf')
        best_dv_vec = None
        best_new_miss = 0.0

        # Try small increments of delta-v up to 5 m/s
        for dv_mag in [0.1, 0.5, 1.0, 2.0, 5.0]:
            for direction in [1.0, -1.0]:  # Prograde / Retrograde
                dv_vec = v_unit * dv_mag * 0.001  # convert m/s to km/s
                dv_vec *= direction
                
                # Apply impulsive burn
                maneuvered_sat = sat_at_burn.copy()
                maneuvered_sat[3:] += dv_vec
                
                # Propagate to new TCA
                time_remaining = tca_s - burn_lead_time_s
                new_tca_s, new_miss, _, _ = self._tca_calculator.compute_tca(
                    maneuvered_sat, debris_at_burn, max_time=time_remaining + 600.0
                )
                
                if new_miss >= self.target_miss_km:
                    if dv_mag < best_dv_mag:
                        best_dv_mag = dv_mag
                        best_dv_vec = dv_vec
                        best_new_miss = new_miss

        if best_dv_vec is not None:
            return {
                "maneuver_id": str(uuid.uuid4()),
                "delta_v_ms": best_dv_mag,
                "direction": "prograde" if np.dot(best_dv_vec, v_unit) > 0 else "retrograde",
                "time_to_burn_s": burn_lead_time_s,
                "predicted_new_miss_km": best_new_miss,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return None
