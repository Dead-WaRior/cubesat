"""Integration tests that exercise multiple subsystems together."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
from fastapi.testclient import TestClient

from ingestion.api import app
from ingestion.queue_manager import QueueManager
from prediction.risk_assessor import RiskAssessor
from shared.schemas import TelemetryPacket
from simulation.engine import SimulationEngine
from vision.preprocessing import ImagePreprocessor

_CLIENT = TestClient(app)


# ---------------------------------------------------------------------------
# Schema serialisation
# ---------------------------------------------------------------------------


def test_schema_to_json_and_back() -> None:
    packet = TelemetryPacket(
        timestamp=datetime.now(timezone.utc),
        satellite_position={"x": 6771.0, "y": 100.0, "z": 0.0},
        velocity={"vx": -0.5, "vy": 7.68, "vz": 0.0},
        attitude_quaternion=[1.0, 0.0, 0.0, 0.0],
        frame_id="integration_test_frame",
    )
    json_str = packet.model_dump_json()
    data = json.loads(json_str)
    restored = TelemetryPacket.model_validate(data)
    assert restored.frame_id == packet.frame_id
    assert restored.satellite_position == packet.satellite_position


# ---------------------------------------------------------------------------
# Full simulation → vision pipeline
# ---------------------------------------------------------------------------


def test_full_simulation_frame_pipeline() -> None:
    engine = SimulationEngine(scenario_name="safe_flyby")
    frame, telemetry = engine.generate_frame()

    preprocessor = ImagePreprocessor()
    processed = preprocessor.preprocess(frame)

    assert processed.shape == frame.shape
    assert processed.dtype == np.uint8
    assert telemetry.frame_id.startswith("frame_")


# ---------------------------------------------------------------------------
# Safe flyby scenario
# ---------------------------------------------------------------------------


def test_safe_flyby_no_critical_alert() -> None:
    assessor = RiskAssessor()
    # Values consistent with a safe fly-by: low Pc, large miss, long TCA
    alert = assessor.assess(
        track_id=99,
        pc=1e-9,
        miss_distance_km=200.0,
        tca_seconds=10800.0,
    )
    assert alert is None


# ---------------------------------------------------------------------------
# QueueManager
# ---------------------------------------------------------------------------


def test_queue_manager_drops_old() -> None:
    qm = QueueManager(maxlen=3)
    for i in range(5):
        qm.enqueue(f"item_{i}")
    # Only 3 items fit; oldest (item_0, item_1) should be gone
    assert qm.size() == 3
    first = qm.dequeue()
    assert first == "item_2"


def test_queue_manager_size() -> None:
    qm = QueueManager(maxlen=10)
    assert qm.size() == 0
    qm.enqueue("a")
    qm.enqueue("b")
    assert qm.size() == 2
    qm.dequeue()
    assert qm.size() == 1


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def test_health_endpoint() -> None:
    response = _CLIENT.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "timestamp" in body
