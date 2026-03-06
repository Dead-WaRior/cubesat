"""YAML-backed configuration for the simulation engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_NOISE_CONFIG: dict[str, Any] = {
    "gaussian_sigma": 2.0,
    "hot_pixel_density": 0.001,
    "cosmic_ray_probability": 0.01,
}


@dataclass
class SimulationConfig:
    """Runtime configuration for the simulation engine.

    Attributes:
        width: Frame width in pixels.
        height: Frame height in pixels.
        frame_rate: Simulation playback rate in frames per second.
        num_stars: Number of background stars to render.
        noise_config: Noise pipeline parameters (see
            :func:`simulation.noise.apply_all_noise`).
        scenario_name: Name of the active scenario (used to locate the YAML
            file under ``simulation/scenarios/``).
    """

    width: int = 640
    height: int = 480
    frame_rate: float = 10.0
    num_stars: int = 200
    noise_config: dict[str, Any] = field(default_factory=lambda: dict(_DEFAULT_NOISE_CONFIG))
    scenario_name: str = "safe_flyby"


def load_config(path: str) -> SimulationConfig:
    """Load a :class:`SimulationConfig` from a YAML file.

    If the file does not exist a default configuration is returned and a
    warning is logged.

    Args:
        path: Filesystem path to the YAML configuration file.

    Returns:
        Populated :class:`SimulationConfig` instance.
    """
    config_path = Path(path)
    if not config_path.exists():
        logger.warning("Config file not found at '%s', using defaults.", path)
        return SimulationConfig()

    with config_path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    noise_config = {**_DEFAULT_NOISE_CONFIG, **raw.get("noise", {})}

    return SimulationConfig(
        width=int(raw.get("width", 640)),
        height=int(raw.get("height", 480)),
        frame_rate=float(raw.get("frame_rate", 10.0)),
        num_stars=int(raw.get("num_stars", 200)),
        noise_config=noise_config,
        scenario_name=str(raw.get("scenario_name", "safe_flyby")),
    )


def save_config(config: SimulationConfig, path: str) -> None:
    """Serialise *config* to a YAML file at *path*.

    Parent directories are created automatically.

    Args:
        config: Configuration object to persist.
        path: Destination filesystem path for the YAML file.
    """
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {
        "width": config.width,
        "height": config.height,
        "frame_rate": config.frame_rate,
        "num_stars": config.num_stars,
        "noise": config.noise_config,
        "scenario_name": config.scenario_name,
    }

    with config_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False, sort_keys=True)

    logger.debug("Saved simulation config to '%s'.", path)
