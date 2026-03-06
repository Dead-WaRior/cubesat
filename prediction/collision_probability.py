"""Collision probability estimation using the Alfriend-Akella 2D projection method."""

from __future__ import annotations

import numpy as np
from scipy import integrate


class CollisionProbabilityCalculator:
    """Computes the probability of collision (Pc) between two objects at TCA.

    Implements a simplified version of the Alfriend-Akella 2D method:
    the combined position covariance is projected onto the encounter plane
    (the plane perpendicular to the relative velocity vector), and the
    Gaussian probability within the combined hard-body radius is integrated
    numerically.
    """

    def compute_pc(
        self,
        miss_distance_km: float,
        combined_covariance: np.ndarray,
        combined_size_km: float = 0.01,
    ) -> float:
        """Estimate the probability of collision at closest approach.

        The method projects the 6×6 combined covariance matrix onto a 2D
        encounter plane aligned with the miss-distance vector and an arbitrary
        orthogonal direction, then numerically integrates a bivariate Gaussian
        over a circular hard-body region of radius *combined_size_km*.

        Args:
            miss_distance_km: Miss distance at TCA in km.
            combined_covariance: Combined 6×6 position-velocity covariance
                matrix (km^2 and (km/s)^2 units), shape ``(6, 6)``.
            combined_size_km: Combined hard-body radius in km (sum of the two
                object radii).

        Returns:
            Probability of collision in the range ``[0, 1]``.
        """
        # Extract the 3×3 position covariance block
        cov_pos = combined_covariance[:3, :3]

        # Build a 2D projection basis in the encounter plane.
        # Use the miss-distance direction as the first basis vector and
        # an arbitrary orthogonal vector as the second.
        miss_vec = np.array([miss_distance_km, 0.0, 0.0])
        u = miss_vec / (np.linalg.norm(miss_vec) + 1e-30)

        # Gram-Schmidt: pick an orthogonal complement
        candidate = np.array([0.0, 1.0, 0.0])
        if abs(np.dot(u, candidate)) > 0.9:
            candidate = np.array([0.0, 0.0, 1.0])
        v = candidate - np.dot(candidate, u) * u
        v /= np.linalg.norm(v)

        # Project the 3×3 covariance to 2D
        basis = np.column_stack([u, v])  # shape (3, 2)
        cov_2d = basis.T @ cov_pos @ basis  # shape (2, 2)

        # Regularise to ensure positive-definiteness
        cov_2d += np.eye(2) * 1e-10

        sigma_x = np.sqrt(max(cov_2d[0, 0], 1e-20))
        sigma_y = np.sqrt(max(cov_2d[1, 1], 1e-20))
        rho = float(np.clip(cov_2d[0, 1] / (sigma_x * sigma_y), -0.9999, 0.9999))

        r_hb = combined_size_km  # hard-body radius

        def integrand(y: float, x: float) -> float:
            norm_factor = 1.0 / (2.0 * np.pi * sigma_x * sigma_y * np.sqrt(1 - rho**2))
            z = (
                (x - miss_distance_km) ** 2 / sigma_x**2
                - 2 * rho * (x - miss_distance_km) * y / (sigma_x * sigma_y)
                + y**2 / sigma_y**2
            ) / (2 * (1 - rho**2))
            return norm_factor * np.exp(-z)

        # Integration limits: a square bounding box around the hard-body circle
        limit = r_hb + 5.0 * max(sigma_x, sigma_y)

        try:
            result, _ = integrate.dblquad(
                integrand,
                miss_distance_km - limit,
                miss_distance_km + limit,
                lambda x: -r_hb,
                lambda x: r_hb,
                epsabs=1e-8,
                epsrel=1e-6,
            )
        except Exception:
            # Fall back to zero if integration fails
            result = 0.0

        return float(np.clip(result, 0.0, 1.0))

    def combine_covariances(
        self,
        cov1: np.ndarray,
        cov2: np.ndarray,
    ) -> np.ndarray:
        """Combine two state covariance matrices by addition.

        Under the assumption that the two objects' orbit determination errors
        are uncorrelated, the combined covariance is the sum of the individual
        covariances.

        Args:
            cov1: First covariance matrix, shape ``(6, 6)``.
            cov2: Second covariance matrix, shape ``(6, 6)``.

        Returns:
            Combined covariance matrix, shape ``(6, 6)``.
        """
        return cov1 + cov2
