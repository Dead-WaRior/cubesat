"""Standalone CLI runner for the CubeSat simulation engine."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional


from simulation.engine import SimulationEngine
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed :class:`argparse.Namespace`.
    """
    parser = argparse.ArgumentParser(
        description="Run the CubeSat simulation engine and optionally save frames to disk.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--scenario",
        default="safe_flyby",
        help="Scenario name matching a YAML file in simulation/scenarios/.",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=100,
        help="Number of frames to generate (overrides scenario duration).",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=None,
        help="Directory where PNG frames are saved.  Skipped if not set.",
    )
    parser.add_argument(
        "--redis",
        action="store_true",
        default=False,
        help="Push generated frames to the Redis stream.",
    )
    parser.add_argument(
        "--api-url",
        dest="api_url",
        default="http://localhost:8000",
        help="URL of the ingestion API to push frames to.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    """Entry point for the standalone simulation runner.

    Args:
        argv: Optional argument list for programmatic invocation.
    """
    args = _parse_args(argv)

    output_dir: Optional[Path] = None
    if args.output_dir is not None:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Saving frames to '%s'.", output_dir)

    engine = SimulationEngine(scenario_name=args.scenario)

    logger.info(
        "Starting simulation: scenario='%s', frames=%d, redis=%s",
        args.scenario,
        args.frames,
        args.redis,
    )

    for idx, (image_frame, telemetry) in enumerate(
        engine.run(num_frames=args.frames, push_to_redis=args.redis)
    ):
        if (idx + 1) % 10 == 0 or idx == 0:
            logger.info(
                "Frame %d/%d  frame_id=%s  pos=(%.1f, %.1f, %.1f) km",
                idx + 1,
                args.frames,
                image_frame.frame_id,
                telemetry.satellite_position["x"],
                telemetry.satellite_position["y"],
                telemetry.satellite_position["z"],
            )

        if output_dir is not None:
            import base64

            png_bytes = base64.b64decode(image_frame.image_data)
            frame_path = output_dir / f"frame_{idx:06d}.png"
            frame_path.write_bytes(png_bytes)

        if args.api_url:
            try:
                with httpx.Client(timeout=2.0) as client:
                    client.post(f"{args.api_url}/frames", json=image_frame.model_dump(mode='json'))
                    client.post(f"{args.api_url}/telemetry", json=telemetry.model_dump(mode='json'))
            except Exception as exc:
                logger.warning("Ingestion API push failed: %s", exc)

    logger.info("Done.")


if __name__ == "__main__":
    main()
