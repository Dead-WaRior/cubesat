"""Main simulation engine: orchestrates star field, debris, noise, and telemetry."""

from __future__ import annotations

import base64
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

import cv2
import numpy as np
import yaml

from shared.schemas import ImageFrame, TelemetryPacket
from simulation.debris import DebrisObject, DebrisScenario
from simulation.noise import apply_all_noise
from simulation.star_field import StarField
from simulation.telemetry import TelemetryGenerator

logger = logging.getLogger(__name__)

_SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def _load_scenario(scenario_name: str) -> DebrisScenario:
    """Load a :class:`DebrisScenario` from the scenarios directory YAML.

    Args:
        scenario_name: Base name of the scenario file (without ``.yaml``).

    Returns:
        Populated :class:`DebrisScenario`.  Falls back to an empty scenario if
        the file cannot be found or parsed.
    """
    if scenario_name == "random":
        import random
        debris_list = []
        num_debris = random.randint(5, 12)
        for i in range(num_debris):
            if i < 2:
                # Force a couple of objects on a collision/close-approach path
                # Image center is approx 320x240
                x = random.uniform(500, 700)
                y = random.uniform(300, 500)
                dx, dy = 320 - x, 240 - y
                norm = (dx**2 + dy**2)**0.5
                speed = random.uniform(2.0, 5.0)
                vx, vy = (dx/norm)*speed, (dy/norm)*speed
                rng = random.uniform(1.5, 8.0)
            else:
                x = random.uniform(-100, 700)
                y = random.uniform(-100, 500)
                vx = random.uniform(-8.0, 8.0)
                vy = random.uniform(-8.0, 8.0)
                rng = random.uniform(15.0, 80.0)
                
            debris_list.append(DebrisObject(
                debris_id=i+1, x=x, y=y, vx=vx, vy=vy,
                size=random.uniform(1.0, 3.5),
                brightness=random.randint(150, 255),
                debris_type=random.choice(["streak", "blob", "point"]),
                range_km=rng
            ))
        return DebrisScenario(name="Randomized Environment", debris_list=debris_list, duration_frames=600, frame_rate=10.0)

    yaml_path = _SCENARIOS_DIR / f"{scenario_name}.yaml"
    if not yaml_path.exists():
        logger.warning("Scenario file not found: '%s'. Using empty scenario.", yaml_path)
        return DebrisScenario(name=scenario_name)

    with yaml_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    debris_list: list[DebrisObject] = []
    for entry in raw.get("debris", []):
        debris_list.append(
            DebrisObject(
                debris_id=int(entry["id"]),
                x=float(entry["x"]),
                y=float(entry["y"]),
                vx=float(entry["vx"]),
                vy=float(entry["vy"]),
                size=float(entry.get("size", 2.0)),
                brightness=int(entry.get("brightness", 200)),
                debris_type=str(entry.get("type", "streak")),
                range_km=float(entry.get("range_km", 50.0)),
            )
        )

    return DebrisScenario(
        name=raw.get("name", scenario_name),
        debris_list=debris_list,
        duration_frames=int(raw.get("duration_frames", 300)),
        frame_rate=float(raw.get("frame_rate", 10.0)),
    )


class SimulationEngine:
    """Orchestrates synthetic frame generation for the CubeSat simulation.

    Combines a static star-field background with kinematic debris objects,
    sensor noise, and paired telemetry packets to produce a continuous stream
    of :class:`~shared.schemas.ImageFrame` / :class:`~shared.schemas.TelemetryPacket`
    pairs that downstream subsystems (ingestion, detection, prediction) consume.

    Args:
        config_path: Optional path to a YAML engine config file.  Currently
            used only if callers want to override width/height/num_stars
            independently of the scenario; the scenario YAML takes precedence
            for noise and debris parameters.
        scenario_name: Name of the scenario to load from
            ``simulation/scenarios/{scenario_name}.yaml``.
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        scenario_name: str = "safe_flyby",
    ) -> None:
        self._scenario = _load_scenario(scenario_name)
        logger.info(
            "Loaded scenario '%s' with %d debris object(s), %d frames.",
            self._scenario.name,
            len(self._scenario.debris_list),
            self._scenario.duration_frames,
        )

        # Resolve frame dimensions from scenario YAML (fall-through to defaults)
        scenario_yaml_path = _SCENARIOS_DIR / f"{scenario_name}.yaml"
        width, height, noise_cfg = 640, 480, {}
        if scenario_yaml_path.exists():
            with scenario_yaml_path.open("r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            width = int(raw.get("width", 640))
            height = int(raw.get("height", 480))
            noise_cfg = raw.get("noise", {})

        self._width = width
        self._height = height
        self._noise_config: dict = noise_cfg
        self._frame_rate: float = self._scenario.frame_rate

        self._star_field = StarField(width=width, height=height)
        self._base_stars: np.ndarray = self._star_field.generate()

        self._telemetry_gen = TelemetryGenerator(frame_rate=self._frame_rate)

        self._frame_counter: int = 0

        # Optional Redis client (skip gracefully if unavailable)
        self._redis_client = None
        try:
            from ingestion.redis_client import RedisStreamClient

            client = RedisStreamClient()
            if client.health_check():
                self._redis_client = client
                logger.info("Redis client connected.")
            else:
                logger.info("Redis unavailable – running without stream publishing.")
        except Exception:
            logger.info("Redis client could not be initialised – skipping.")

    # ------------------------------------------------------------------
    # Frame generation
    # ------------------------------------------------------------------

    def generate_frame(self) -> tuple[np.ndarray, TelemetryPacket]:
        """Generate a single synthetic frame and paired telemetry packet.

        Steps:
        1. Start from the pre-rendered star-field background.
        2. Update and render each visible debris object.
        3. Apply the noise pipeline.
        4. Generate a telemetry packet for the current orbital state.

        Returns:
            Tuple of ``(frame_image, telemetry)`` where *frame_image* is a
            ``uint8`` NumPy array of shape ``(height, width)`` and *telemetry*
            is a populated :class:`~shared.schemas.TelemetryPacket`.
        """
        frame_id = f"frame_{self._frame_counter:06d}_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(tz=timezone.utc)

        # Composite debris onto star field
        image: np.ndarray = self._base_stars.copy()
        for obj in self._scenario.debris_list:
            obj.update_position()
            if obj.is_visible(self._width, self._height):
                image = obj.render(image)

        # Noise pipeline
        image = apply_all_noise(image, self._noise_config)

        telemetry = self._telemetry_gen.generate(frame_id=frame_id, timestamp=timestamp)
        self._frame_counter += 1
        return image, telemetry

    def frame_to_image_frame(
        self,
        frame: np.ndarray,
        telemetry: TelemetryPacket,
    ) -> ImageFrame:
        """Convert a raw NumPy frame array into an :class:`~shared.schemas.ImageFrame`.

        The array is PNG-encoded and stored as a Base64 string inside the
        returned model.

        Args:
            frame: Grayscale ``uint8`` image array of shape ``(H, W)``.
            telemetry: Telemetry packet whose ``frame_id`` is reused.

        Returns:
            Populated :class:`~shared.schemas.ImageFrame` ready for ingestion.
        """
        success, buf = cv2.imencode(".png", frame)
        if not success:
            raise RuntimeError(f"cv2.imencode failed for frame {telemetry.frame_id}")

        image_b64 = base64.b64encode(buf.tobytes()).decode("ascii")
        h, w = frame.shape[:2]

        return ImageFrame(
            frame_id=telemetry.frame_id,
            timestamp=telemetry.timestamp,
            image_data=image_b64,
            width=w,
            height=h,
            exposure_ms=10.0,
            metadata={"scenario": self._scenario.name, "frame_index": self._frame_counter - 1},
        )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(
        self,
        num_frames: Optional[int] = None,
        push_to_redis: bool = False,
    ) -> Generator[tuple[ImageFrame, TelemetryPacket], None, None]:
        """Generate frames continuously, yielding ``(ImageFrame, TelemetryPacket)`` pairs.

        Args:
            num_frames: Stop after this many frames.  If *None*, run for the
                full scenario duration (``scenario.duration_frames``).
            push_to_redis: When ``True`` (and Redis is reachable), publish each
                frame + telemetry pair to the ``frames`` Redis stream.

        Yields:
            ``(ImageFrame, TelemetryPacket)`` for each generated frame.
        """
        total = num_frames if num_frames is not None else self._scenario.duration_frames
        frame_interval = 1.0 / self._frame_rate

        logger.info(
            "Starting simulation run: scenario='%s', frames=%d, fps=%.1f",
            self._scenario.name,
            total,
            self._frame_rate,
        )

        for _ in range(total):
            loop_start = time.monotonic()

            raw_frame, telemetry = self.generate_frame()
            image_frame = self.frame_to_image_frame(raw_frame, telemetry)

            if push_to_redis and self._redis_client is not None:
                try:
                    self._redis_client.push_frame(image_frame, telemetry)
                except Exception as exc:
                    logger.warning("Redis push failed: %s", exc)

            yield image_frame, telemetry

            # Respect frame rate (sleep off any remaining time in the interval)
            elapsed = time.monotonic() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.info("Simulation run complete: %d frames generated.", total)
