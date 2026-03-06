"""Tests for prediction/risk_assessor.py RiskAssessor."""

from __future__ import annotations


from prediction.risk_assessor import RiskAssessor
from shared.schemas import AlertLevel

_ASSESSOR = RiskAssessor()


def test_no_alert_safe_distance() -> None:
    # Large miss distance, low Pc, long TCA → no alert
    alert = _ASSESSOR.assess(
        track_id=1,
        pc=1e-8,
        miss_distance_km=50.0,
        tca_seconds=7200.0,
    )
    assert alert is None


def test_advisory_alert() -> None:
    # Pc just above PC_ADVISORY threshold
    alert = _ASSESSOR.assess(
        track_id=2,
        pc=2e-5,
        miss_distance_km=20.0,
        tca_seconds=3600.0,
    )
    assert alert is not None
    assert alert.alert_level == AlertLevel.ADVISORY


def test_warning_alert() -> None:
    # Pc above PC_WARNING
    alert = _ASSESSOR.assess(
        track_id=3,
        pc=2e-4,
        miss_distance_km=20.0,
        tca_seconds=3600.0,
    )
    assert alert is not None
    assert alert.alert_level == AlertLevel.WARNING


def test_critical_alert_pc() -> None:
    # Pc above PC_CRITICAL
    alert = _ASSESSOR.assess(
        track_id=4,
        pc=2e-3,
        miss_distance_km=20.0,
        tca_seconds=3600.0,
    )
    assert alert is not None
    assert alert.alert_level == AlertLevel.CRITICAL


def test_critical_alert_tca() -> None:
    # TCA below TCA_CRITICAL_S (900 s) triggers CRITICAL regardless of Pc
    alert = _ASSESSOR.assess(
        track_id=5,
        pc=1e-8,
        miss_distance_km=50.0,
        tca_seconds=500.0,
    )
    assert alert is not None
    assert alert.alert_level == AlertLevel.CRITICAL


def test_alert_recommended_actions() -> None:
    cases = [
        (AlertLevel.ADVISORY, dict(pc=2e-5, miss_distance_km=20.0, tca_seconds=3600.0)),
        (AlertLevel.WARNING, dict(pc=2e-4, miss_distance_km=20.0, tca_seconds=3600.0)),
        (AlertLevel.CRITICAL, dict(pc=2e-3, miss_distance_km=20.0, tca_seconds=3600.0)),
    ]
    for expected_level, kwargs in cases:
        alert = _ASSESSOR.assess(track_id=10, **kwargs)
        assert alert is not None
        assert alert.alert_level == expected_level
        assert len(alert.recommended_action) > 0
