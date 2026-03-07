"""Risk assessment logic: maps collision metrics to actionable alert levels."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from shared.schemas import AlertLevel, RiskAlert


class RiskAssessor:
    """Evaluates collision risk metrics and generates :class:`~shared.schemas.RiskAlert` objects.

    Thresholds follow standard conjunction data message (CDM) conventions,
    with three escalating alert levels:

    * **ADVISORY** – elevated monitoring warranted (Pc > 1 × 10⁻⁵ or range < 10 km).
    * **WARNING**  – manoeuvre planning should begin (Pc > 1 × 10⁻⁴ or range < 5 km).
    * **CRITICAL** – immediate action required (Pc > 1 × 10⁻³ or TCA < 900 s).
    """

    # ------------------------------------------------------------------
    # Alert thresholds
    # ------------------------------------------------------------------
    PC_ADVISORY: float = 1e-5
    PC_WARNING: float = 1e-4
    PC_CRITICAL: float = 1e-3

    RANGE_ADVISORY_KM: float = 15.0
    RANGE_WARNING_KM: float = 8.0
    RANGE_CRITICAL_KM: float = 2.0

    TCA_ADVISORY_S: float = 45.0
    TCA_WARNING_S: float = 25.0
    TCA_CRITICAL_S: float = 10.0  # Scaled down to fit 20s simulation loop

    # ------------------------------------------------------------------
    # Recommended actions
    # ------------------------------------------------------------------
    _ACTION_CRITICAL: str = "Initiate emergency collision avoidance maneuver"
    _ACTION_WARNING: str = "Review maneuver plan, prepare avoidance burn"
    _ACTION_ADVISORY: str = "Increase monitoring frequency, prepare contingency"

    def assess(
        self,
        track_id: int,
        pc: float,
        miss_distance_km: float,
        tca_seconds: float,
    ) -> Optional[RiskAlert]:
        """Evaluate collision risk and return an alert if any threshold is exceeded.

        Thresholds are checked in descending severity order.  The first
        (highest) level whose condition is met determines the alert level
        returned.

        Args:
            track_id: Identifier of the debris track being assessed.
            pc: Estimated probability of collision in ``[0, 1]``.
            miss_distance_km: Predicted miss distance at TCA in km.
            tca_seconds: Predicted time to closest approach in seconds.

        Returns:
            A :class:`~shared.schemas.RiskAlert` if any threshold is exceeded,
            otherwise ``None``.
        """
        level: Optional[AlertLevel] = None
        action: str = ""

        if (
            pc > self.PC_CRITICAL
            or tca_seconds < self.TCA_CRITICAL_S
            or miss_distance_km < self.RANGE_CRITICAL_KM
        ):
            level = AlertLevel.CRITICAL
            action = self._ACTION_CRITICAL
        elif (
            pc > self.PC_WARNING
            or miss_distance_km < self.RANGE_WARNING_KM
            or tca_seconds < self.TCA_WARNING_S
        ):
            level = AlertLevel.WARNING
            action = self._ACTION_WARNING
        elif (
            pc > self.PC_ADVISORY
            or miss_distance_km < self.RANGE_ADVISORY_KM
            or tca_seconds < self.TCA_ADVISORY_S
        ):
            level = AlertLevel.ADVISORY
            action = self._ACTION_ADVISORY

        if level is None:
            return None

        return RiskAlert(
            alert_id=str(uuid.uuid4()),
            track_id=track_id,
            alert_level=level,
            probability_of_collision=float(pc),
            time_to_closest_approach=float(tca_seconds),
            miss_distance_km=float(miss_distance_km),
            recommended_action=action,
            timestamp=datetime.now(timezone.utc),
        )
