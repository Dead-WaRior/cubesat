"""Tests for the simulation layer (star_field, debris, noise, telemetry, engine)."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from simulation.debris import DebrisObject
from simulation.engine import SimulationEngine
from simulation.noise import add_gaussian_noise, add_hot_pixels
from simulation.star_field import StarField
from simulation.telemetry import TelemetryGenerator


# ---------------------------------------------------------------------------
# StarField
# ---------------------------------------------------------------------------


def test_star_field_shape() -> None:
    sf = StarField(width=640, height=480, seed=0)
    img = sf.generate()
    assert img.shape == (480, 640)
    assert img.dtype == np.uint8


def test_star_field_has_stars() -> None:
    sf = StarField(width=640, height=480, num_stars=200, seed=42)
    img = sf.generate()
    # Stars are bright pixels; at least some should exceed 50
    assert np.any(img > 50)


def test_star_field_reproducible() -> None:
    sf1 = StarField(width=640, height=480, seed=7)
    sf2 = StarField(width=640, height=480, seed=7)
    np.testing.assert_array_equal(sf1.generate(), sf2.generate())


# ---------------------------------------------------------------------------
# DebrisObject
# ---------------------------------------------------------------------------


def test_debris_object_update() -> None:
    obj = DebrisObject(debris_id=1, x=100.0, y=200.0, vx=3.0, vy=-2.0)
    obj.update_position(dt=1.0)
    assert obj.x == pytest.approx(103.0)
    assert obj.y == pytest.approx(198.0)


def test_debris_render_returns_image() -> None:
    obj = DebrisObject(debris_id=1, x=320.0, y=240.0, vx=5.0, vy=2.0, debris_type="streak")
    background = np.zeros((480, 640), dtype=np.uint8)
    rendered = obj.render(background)
    assert rendered.shape == background.shape
    assert rendered.dtype == np.uint8


# ---------------------------------------------------------------------------
# Noise functions
# ---------------------------------------------------------------------------


def test_noise_gaussian() -> None:
    uniform = np.full((100, 100), 128, dtype=np.uint8)
    noisy = add_gaussian_noise(uniform, sigma=5.0, rng=np.random.default_rng(0))
    # The noisy image must differ from the original
    assert not np.array_equal(noisy, uniform)


def test_noise_hot_pixels() -> None:
    dark = np.zeros((100, 100), dtype=np.uint8)
    result = add_hot_pixels(dark, density=0.01, rng=np.random.default_rng(1))
    # Some pixels must now be bright
    assert np.any(result > 200)


# ---------------------------------------------------------------------------
# TelemetryGenerator
# ---------------------------------------------------------------------------


def test_telemetry_generator() -> None:
    gen = TelemetryGenerator(frame_rate=10.0, seed=0)
    packet = gen.generate(frame_id="frame_001", timestamp=datetime.now(timezone.utc))
    assert packet.frame_id == "frame_001"
    assert "x" in packet.satellite_position
    assert len(packet.attitude_quaternion) == 4


# ---------------------------------------------------------------------------
# SimulationEngine
# ---------------------------------------------------------------------------


def test_simulation_engine_frame() -> None:
    engine = SimulationEngine(scenario_name="safe_flyby")
    frame, telemetry = engine.generate_frame()
    assert frame.shape == (480, 640)
    assert frame.dtype == np.uint8
    assert telemetry.frame_id.startswith("frame_")


def test_simulation_engine_10_frames() -> None:
    engine = SimulationEngine(scenario_name="safe_flyby")
    for _ in range(10):
        frame, telemetry = engine.generate_frame()
        assert frame.shape == (480, 640)
        assert telemetry.frame_id != ""
