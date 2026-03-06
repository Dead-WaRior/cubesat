"""Redis Streams producer/consumer client for the CubeSat data pipeline."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from shared.schemas import DetectionEvent, ImageFrame, RiskAlert, TelemetryPacket

logger = logging.getLogger(__name__)

_STREAM_FRAMES = "frames"
_STREAM_DETECTIONS = "detections"
_STREAM_ALERTS = "alerts"


class RedisStreamClient:
    """Thin wrapper around Redis Streams for the CubeSat data pipeline.

    Each public ``push_*`` method serialises a Pydantic model to JSON and
    appends it to the appropriate stream.  Each ``read_*`` method returns raw
    message dicts straight from the Redis client so that callers can apply
    whatever deserialisation strategy they need.

    Args:
        host: Redis server hostname.  Defaults to ``"redis"`` (Docker service
            name) so the client works out-of-the-box inside the compose stack.
        port: Redis server port.  Defaults to ``6379``.
        db: Redis logical database index.  Defaults to ``0``.
    """

    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        db: int = 0,
    ) -> None:
        self._client: redis.Redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
        )
        logger.debug("RedisStreamClient initialised (host=%s port=%d db=%d)", host, port, db)

    # ------------------------------------------------------------------
    # Producers
    # ------------------------------------------------------------------

    def push_frame(self, frame: ImageFrame, telemetry: TelemetryPacket) -> str:
        """Append a frame + telemetry pair to the ``frames`` stream.

        Args:
            frame: Captured image frame model.
            telemetry: Telemetry snapshot associated with *frame*.

        Returns:
            The Redis stream entry ID assigned to the new message.

        Raises:
            redis.ConnectionError: Re-raised after logging if the server is
                unreachable.
        """
        try:
            entry_id: str = self._client.xadd(
                _STREAM_FRAMES,
                {
                    "frame": frame.model_dump_json(),
                    "telemetry": telemetry.model_dump_json(),
                },
            )
            logger.debug("Pushed frame %s → entry %s", frame.frame_id, entry_id)
            return entry_id
        except redis.ConnectionError:
            logger.error("Redis unavailable – failed to push frame %s", frame.frame_id)
            raise

    def push_detection(self, detection: DetectionEvent) -> str:
        """Append a detection event to the ``detections`` stream.

        Args:
            detection: Detection event model to publish.

        Returns:
            The Redis stream entry ID assigned to the new message.

        Raises:
            redis.ConnectionError: Re-raised after logging if the server is
                unreachable.
        """
        try:
            entry_id: str = self._client.xadd(
                _STREAM_DETECTIONS,
                {"detection": detection.model_dump_json()},
            )
            logger.debug(
                "Pushed detection track_id=%d frame=%s → entry %s",
                detection.track_id,
                detection.frame_id,
                entry_id,
            )
            return entry_id
        except redis.ConnectionError:
            logger.error("Redis unavailable – failed to push detection for track %d", detection.track_id)
            raise

    def push_alert(self, alert: RiskAlert) -> str:
        """Append a risk alert to the ``alerts`` stream.

        Args:
            alert: Risk alert model to publish.

        Returns:
            The Redis stream entry ID assigned to the new message.

        Raises:
            redis.ConnectionError: Re-raised after logging if the server is
                unreachable.
        """
        try:
            entry_id: str = self._client.xadd(
                _STREAM_ALERTS,
                {"alert": alert.model_dump_json()},
            )
            logger.debug(
                "Pushed alert %s (level=%s) → entry %s",
                alert.alert_id,
                alert.alert_level,
                entry_id,
            )
            return entry_id
        except redis.ConnectionError:
            logger.error("Redis unavailable – failed to push alert %s", alert.alert_id)
            raise

    # ------------------------------------------------------------------
    # Consumers
    # ------------------------------------------------------------------

    def read_frames(
        self,
        count: int = 10,
        last_id: str = "0-0",
    ) -> list[dict[str, Any]]:
        """Read up to *count* messages from the ``frames`` stream.

        Args:
            count: Maximum number of messages to return.
            last_id: Return only messages with IDs *greater than* this value.
                Pass ``"0-0"`` to read from the beginning.

        Returns:
            A (possibly empty) list of ``{"id": ..., "data": {...}}`` dicts.

        Raises:
            redis.ConnectionError: Re-raised after logging if the server is
                unreachable.
        """
        return self._read_stream(_STREAM_FRAMES, count=count, last_id=last_id)

    def read_detections(
        self,
        count: int = 10,
        last_id: str = "0-0",
    ) -> list[dict[str, Any]]:
        """Read up to *count* messages from the ``detections`` stream.

        Args:
            count: Maximum number of messages to return.
            last_id: Return only messages with IDs *greater than* this value.

        Returns:
            A (possibly empty) list of ``{"id": ..., "data": {...}}`` dicts.

        Raises:
            redis.ConnectionError: Re-raised after logging if the server is
                unreachable.
        """
        return self._read_stream(_STREAM_DETECTIONS, count=count, last_id=last_id)

    def read_alerts(
        self,
        count: int = 10,
        last_id: str = "0-0",
    ) -> list[dict[str, Any]]:
        """Read up to *count* messages from the ``alerts`` stream.

        Args:
            count: Maximum number of messages to return.
            last_id: Return only messages with IDs *greater than* this value.

        Returns:
            A (possibly empty) list of ``{"id": ..., "data": {...}}`` dicts.

        Raises:
            redis.ConnectionError: Re-raised after logging if the server is
                unreachable.
        """
        return self._read_stream(_STREAM_ALERTS, count=count, last_id=last_id)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Ping Redis to verify connectivity.

        Returns:
            ``True`` if the server responds, ``False`` otherwise.
        """
        try:
            return bool(self._client.ping())
        except redis.ConnectionError:
            logger.warning("Redis health check failed – server unreachable")
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_stream(
        self,
        stream: str,
        count: int,
        last_id: str,
    ) -> list[dict[str, Any]]:
        """Read messages from *stream* using ``XREAD``.

        Args:
            stream: Redis stream key.
            count: Maximum number of entries to return.
            last_id: Exclusive lower-bound entry ID.

        Returns:
            A list of ``{"id": str, "data": dict}`` items.
        """
        try:
            response = self._client.xread({stream: last_id}, count=count)
        except redis.ConnectionError:
            logger.error("Redis unavailable – failed to read stream '%s'", stream)
            raise

        if not response:
            return []

        messages: list[dict[str, Any]] = []
        for _stream_name, entries in response:
            for entry_id, fields in entries:
                parsed_fields: dict[str, Any] = {}
                for key, value in fields.items():
                    try:
                        parsed_fields[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        parsed_fields[key] = value
                messages.append({"id": entry_id, "data": parsed_fields})

        return messages
