"""Unscented Kalman Filter tracker for debris objects in ECI frame."""

from __future__ import annotations

from typing import Optional

import numpy as np
from filterpy.kalman import UnscentedKalmanFilter
from filterpy.kalman import MerweScaledSigmaPoints

from prediction.orbital_dynamics import propagate_state


def _fx(state: np.ndarray, dt: float) -> np.ndarray:
    """State transition function used by the UKF.

    Wraps :func:`~prediction.orbital_dynamics.propagate_state` so that filterpy
    can call it with the expected ``(state, dt)`` signature.

    Args:
        state: Current state vector ``[x, y, z, vx, vy, vz]``.
        dt: Time step in seconds.

    Returns:
        Propagated state vector, shape ``(6,)``.
    """
    return propagate_state(state, dt)


def _hx(state: np.ndarray) -> np.ndarray:
    """Measurement function: extract position from full state.

    Args:
        state: State vector ``[x, y, z, vx, vy, vz]``.

    Returns:
        Position measurement ``[x, y, z]``, shape ``(3,)``.
    """
    return state[:3]


class UKFTracker:
    """Tracks a single debris object using an Unscented Kalman Filter.

    The state vector is ``[x, y, z, vx, vy, vz]`` in km and km/s (ECI frame).
    Measurements are ECI position triples ``[x, y, z]`` in km.

    Args:
        track_id: Unique identifier for this track.
        initial_state: Initial state vector ``[x, y, z, vx, vy, vz]``,
            shape ``(6,)``.
        dt: Default propagation time step in seconds.
    """

    #: Diagonal process-noise variance for position components (km^2)
    _Q_POS_VAR: float = 1e-6
    #: Diagonal process-noise variance for velocity components ((km/s)^2)
    _Q_VEL_VAR: float = 1e-8
    #: Diagonal measurement-noise variance for position components (km^2)
    _R_POS_VAR: float = 0.25  # ~500 m 1-sigma

    def __init__(
        self,
        track_id: int,
        initial_state: np.ndarray,
        dt: float = 1.0,
    ) -> None:
        self.track_id = track_id
        self._dt = dt

        points = MerweScaledSigmaPoints(n=6, alpha=1e-3, beta=2.0, kappa=0.0)
        self._ukf = UnscentedKalmanFilter(
            dim_x=6,
            dim_z=3,
            dt=dt,
            fx=_fx,
            hx=_hx,
            points=points,
        )

        self._ukf.x = initial_state.copy().astype(float)
        self._ukf.P = np.diag([1.0, 1.0, 1.0, 0.01, 0.01, 0.01])

        self._ukf.Q = np.diag([
            self._Q_POS_VAR, self._Q_POS_VAR, self._Q_POS_VAR,
            self._Q_VEL_VAR, self._Q_VEL_VAR, self._Q_VEL_VAR,
        ])
        self._ukf.R = np.diag([
            self._R_POS_VAR, self._R_POS_VAR, self._R_POS_VAR,
        ])

    # ------------------------------------------------------------------
    # Core filter operations
    # ------------------------------------------------------------------

    def predict(self, dt: Optional[float] = None) -> np.ndarray:
        """Propagate the filter state forward by one time step.

        Args:
            dt: Time step override in seconds.  Uses the default *dt* from
                ``__init__`` when ``None``.

        Returns:
            Predicted state vector ``[x, y, z, vx, vy, vz]``, shape ``(6,)``.
        """
        step = dt if dt is not None else self._dt
        self._ukf.predict(dt=step)
        return self._ukf.x.copy()

    def update(self, measurement: np.ndarray) -> None:
        """Update the filter with a new ECI position measurement.

        Args:
            measurement: Observed ECI position ``[x, y, z]`` in km,
                shape ``(3,)``.
        """
        self._ukf.update(measurement.astype(float))

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    def get_state(self) -> np.ndarray:
        """Return the current state estimate.

        Returns:
            State vector ``[x, y, z, vx, vy, vz]``, shape ``(6,)``.
        """
        return self._ukf.x.copy()

    def get_covariance(self) -> np.ndarray:
        """Return the current state covariance matrix.

        Returns:
            Covariance matrix, shape ``(6, 6)``.
        """
        return self._ukf.P.copy()

    # ------------------------------------------------------------------
    # Forward propagation
    # ------------------------------------------------------------------

    def propagate_forward(
        self, seconds: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """Propagate the current state estimate forward without mutating the filter.

        Uses the orbital dynamics model directly (not the UKF predict step)
        so that the filter state is preserved for future measurements.

        Args:
            seconds: Number of seconds to propagate forward.

        Returns:
            Tuple of ``(propagated_state, propagated_covariance)`` where
            *propagated_state* has shape ``(6,)`` and *propagated_covariance*
            has shape ``(6, 6)``.
        """
        state = self._ukf.x.copy()
        cov = self._ukf.P.copy()

        dt = self._dt
        remaining = seconds
        while remaining > 0.0:
            step = min(dt, remaining)
            state = propagate_state(state, step)
            remaining -= step

        # Propagate covariance via linearised STM (identity approximation scaled
        # by elapsed time); a full STM would require partial derivatives of the
        # dynamics, which is beyond the scope of this implementation.
        scale = 1.0 + seconds / 3600.0  # covariance grows slowly with time
        propagated_cov = cov * scale

        return state, propagated_cov
