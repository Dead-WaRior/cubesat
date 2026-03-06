"""Closest approach computation for pairs of orbital objects."""

from __future__ import annotations

import numpy as np

from prediction.orbital_dynamics import propagate_state


class ClosestApproachCalculator:
    """Finds the Time of Closest Approach (TCA) between two orbital objects.

    Both objects are propagated forward using the same orbital dynamics model
    (two-body + J2 + drag) in fixed time steps, and the instant of minimum
    separation is identified by scanning the resulting trajectory.
    """

    def compute_tca(
        self,
        sat_state: np.ndarray,
        debris_state: np.ndarray,
        max_time: float = 3600.0,
        dt: float = 1.0,
    ) -> tuple[float, float, np.ndarray, np.ndarray]:
        """Find the Time of Closest Approach between the satellite and a debris object.

        Both states are propagated from *t = 0* up to *max_time* seconds in
        steps of *dt* seconds.  The step with the smallest separation distance
        is returned as the TCA.

        Args:
            sat_state: Satellite state ``[x, y, z, vx, vy, vz]`` in km / km/s,
                shape ``(6,)``.
            debris_state: Debris state ``[x, y, z, vx, vy, vz]`` in km / km/s,
                shape ``(6,)``.
            max_time: Maximum propagation window in seconds.
            dt: Propagation time step in seconds.

        Returns:
            Tuple of:
            - **tca_seconds** (*float*): Time of closest approach in seconds
              from the current epoch.
            - **miss_distance_km** (*float*): Separation distance at TCA in km.
            - **sat_pos_at_tca** (*np.ndarray*): Satellite ECI position at TCA,
              shape ``(3,)``.
            - **debris_pos_at_tca** (*np.ndarray*): Debris ECI position at TCA,
              shape ``(3,)``.
        """
        sat = sat_state.copy().astype(float)
        deb = debris_state.copy().astype(float)

        best_time = 0.0
        best_dist = np.linalg.norm(sat[:3] - deb[:3])
        best_sat_pos = sat[:3].copy()
        best_deb_pos = deb[:3].copy()

        elapsed = 0.0
        while elapsed < max_time:
            step = min(dt, max_time - elapsed)
            sat = propagate_state(sat, step)
            deb = propagate_state(deb, step)
            elapsed += step

            dist = float(np.linalg.norm(sat[:3] - deb[:3]))
            if dist < best_dist:
                best_dist = dist
                best_time = elapsed
                best_sat_pos = sat[:3].copy()
                best_deb_pos = deb[:3].copy()

        return best_time, best_dist, best_sat_pos, best_deb_pos

    def compute_relative_velocity(
        self,
        sat_state: np.ndarray,
        debris_state: np.ndarray,
    ) -> float:
        """Compute the relative velocity magnitude between satellite and debris.

        Args:
            sat_state: Satellite state ``[x, y, z, vx, vy, vz]`` in km / km/s,
                shape ``(6,)``.
            debris_state: Debris state ``[x, y, z, vx, vy, vz]`` in km / km/s,
                shape ``(6,)``.

        Returns:
            Relative velocity magnitude in km/s.
        """
        rel_vel = debris_state[3:6] - sat_state[3:6]
        return float(np.linalg.norm(rel_vel))
