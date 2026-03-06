"""Orbital dynamics functions for CubeSat trajectory propagation.

Provides two-body gravity, J2 oblateness, atmospheric drag, and solar radiation
pressure accelerations, together with a fourth-order Runge-Kutta propagator.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

MU: float = 398600.4418        # Earth gravitational parameter, km^3/s^2
J2: float = 1.08262668e-3      # J2 perturbation coefficient (dimensionless)
R_EARTH: float = 6371.0        # Mean Earth radius, km
RHO_0: float = 1.225e-3        # Reference air density at sea level, kg/m^3
H_SCALE: float = 8.5           # Atmospheric scale height, km
C_D: float = 2.2               # Drag coefficient (dimensionless)
A_M: float = 0.01              # Area-to-mass ratio, m^2/kg


def two_body_accel(pos: np.ndarray, mu: float = MU) -> np.ndarray:
    """Compute two-body gravitational acceleration.

    Args:
        pos: ECI position vector in km, shape ``(3,)``.
        mu: Gravitational parameter in km^3/s^2.

    Returns:
        Gravitational acceleration vector in km/s^2, shape ``(3,)``.
    """
    r = np.linalg.norm(pos)
    return -mu / r**3 * pos


def j2_perturbation(pos: np.ndarray) -> np.ndarray:
    """Compute J2 oblateness perturbation acceleration.

    Args:
        pos: ECI position vector in km, shape ``(3,)``.

    Returns:
        J2 acceleration vector in km/s^2, shape ``(3,)``.
    """
    x, y, z = pos
    r = np.linalg.norm(pos)
    r2 = r**2
    factor = 1.5 * J2 * MU * R_EARTH**2 / r**5
    ax = factor * x * (5 * z**2 / r2 - 1)
    ay = factor * y * (5 * z**2 / r2 - 1)
    az = factor * z * (5 * z**2 / r2 - 3)
    return np.array([ax, ay, az])


def atmospheric_drag(
    pos: np.ndarray,
    vel: np.ndarray,
    cd: float = C_D,
    a_m: float = A_M,
) -> np.ndarray:
    """Compute atmospheric drag deceleration.

    Uses an exponential atmosphere model.  The output has units of km/s^2
    because the density is converted from kg/m^3 to kg/km^3 internally.

    Args:
        pos: ECI position vector in km, shape ``(3,)``.
        vel: ECI velocity vector in km/s, shape ``(3,)``.
        cd: Drag coefficient (dimensionless).
        a_m: Area-to-mass ratio in m^2/kg.

    Returns:
        Drag acceleration vector in km/s^2, shape ``(3,)``.
    """
    r = np.linalg.norm(pos)
    altitude = r - R_EARTH
    rho = RHO_0 * np.exp(-altitude / H_SCALE) * 1e9  # kg/m^3 → kg/km^3
    v = np.linalg.norm(vel)
    if v < 1e-10:
        return np.zeros(3)
    drag = -0.5 * cd * a_m * rho * v * vel
    return drag


def solar_radiation_pressure(
    pos: np.ndarray,
    a_m: float = 0.005,
) -> np.ndarray:
    """Compute solar radiation pressure acceleration (simplified).

    The sun direction is fixed along the ECI *x*-axis and eclipses are
    ignored.  This is suitable for preliminary analysis only.

    Args:
        pos: ECI position vector in km, shape ``(3,)`` (unused in this
            simplified model but kept for API consistency).
        a_m: Area-to-mass ratio in m^2/kg.

    Returns:
        SRP acceleration vector in km/s^2, shape ``(3,)``.
    """
    P_srp = 4.56e-6          # Solar radiation pressure at 1 AU, N/m^2
    C_r = 1.5                # Reflectivity coefficient
    sun_direction = np.array([1.0, 0.0, 0.0])  # simplified: along ECI x-axis
    srp_accel = -P_srp * C_r * a_m * sun_direction * 1e-3  # N/m^2 → km/s^2
    return srp_accel


def propagate_state(
    state: np.ndarray,
    dt: float,
    include_j2: bool = True,
    include_drag: bool = True,
    include_srp: bool = False,
) -> np.ndarray:
    """Propagate an orbital state vector by *dt* seconds using RK4 integration.

    Args:
        state: State vector ``[x, y, z, vx, vy, vz]`` in km and km/s,
            shape ``(6,)``.
        dt: Time step in seconds.
        include_j2: Whether to include J2 oblateness perturbation.
        include_drag: Whether to include atmospheric drag.
        include_srp: Whether to include solar radiation pressure.

    Returns:
        Propagated state vector ``[x, y, z, vx, vy, vz]``, shape ``(6,)``.
    """
    def derivatives(s: np.ndarray) -> np.ndarray:
        pos = s[:3]
        vel = s[3:]
        a = two_body_accel(pos)
        if include_j2:
            a = a + j2_perturbation(pos)
        if include_drag:
            a = a + atmospheric_drag(pos, vel)
        if include_srp:
            a = a + solar_radiation_pressure(pos)
        return np.concatenate([vel, a])

    k1 = derivatives(state)
    k2 = derivatives(state + 0.5 * dt * k1)
    k3 = derivatives(state + 0.5 * dt * k2)
    k4 = derivatives(state + dt * k3)
    return state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
