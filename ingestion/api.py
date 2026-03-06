"""FastAPI application serving the CubeSat collision detection ingestion layer."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import os
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ingestion.queue_manager import QueueManager
from shared.schemas import ImageFrame, TelemetryPacket

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CubeSat Collision Detection API",
    version="1.0.0",
    description="Ingestion layer for satellite image frames, telemetry, and risk alerts.",
)

app.add_middleware(
    CORSMiddleware,
    # Restrict origins in production via the CORS_ORIGINS env var (comma-separated).
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

queue_manager: QueueManager = QueueManager()
recent_alerts: list[dict[str, Any]] = []
active_tracks: list[dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", summary="Health check")
async def health() -> dict[str, Any]:
    """Return the current health status of the ingestion service.

    Returns:
        A JSON object containing ``status`` and ``timestamp``.
    """
    return {"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()}


@app.post("/frames", summary="Ingest an image frame")
async def ingest_frame(frame: ImageFrame) -> dict[str, Any]:
    """Accept an :class:`~shared.schemas.ImageFrame` and add it to the queue.

    Args:
        frame: The image frame payload.

    Returns:
        A JSON object with the ``frame_id`` and a ``queued`` confirmation flag.
    """
    queue_manager.enqueue(frame)
    logger.info("Enqueued frame %s (queue size=%d)", frame.frame_id, queue_manager.size())
    return {"frame_id": frame.frame_id, "queued": True}


@app.post("/telemetry", summary="Ingest a telemetry packet")
async def ingest_telemetry(packet: TelemetryPacket) -> dict[str, Any]:
    """Accept a :class:`~shared.schemas.TelemetryPacket`.

    The telemetry packet is logged and acknowledged.  Downstream consumers
    retrieve it via the Redis stream populated by the simulation service.

    Args:
        packet: The telemetry snapshot.

    Returns:
        A JSON object with the associated ``frame_id`` and a ``received`` flag.
    """
    logger.info("Received telemetry for frame %s", packet.frame_id)
    return {"frame_id": packet.frame_id, "received": True}


@app.get("/tracks", summary="List active tracks")
async def get_tracks() -> list[dict[str, Any]]:
    """Return all currently active object tracks.

    Returns:
        A list of serialised :class:`~shared.schemas.TrackObject` dicts.
        Empty when no tracks are available.
    """
    return active_tracks


@app.get("/alerts", summary="List recent risk alerts")
async def get_alerts() -> list[dict[str, Any]]:
    """Return recently generated collision risk alerts.

    Returns:
        A list of serialised :class:`~shared.schemas.RiskAlert` dicts.
        Empty when no alerts have been raised.
    """
    return recent_alerts


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

_LIVE_PUSH_INTERVAL_S = 0.1  # 100 ms


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    """Stream live system state to connected clients at ~10 Hz.

    The server pushes a JSON message every 100 ms containing the latest frame
    snapshot, active tracks, recent alerts, and subsystem health indicators.

    Args:
        websocket: The connected WebSocket client.
    """
    await websocket.accept()
    logger.info("WebSocket client connected: %s", websocket.client)
    try:
        while True:
            payload: dict[str, Any] = {
                "frame": None,
                "tracks": active_tracks,
                "alerts": recent_alerts,
                "system_health": {
                    "simulation": "ok",
                    "ingestion": "ok",
                    "vision": "ok",
                    "prediction": "ok",
                },
            }
            await websocket.send_text(json.dumps(payload, default=str))
            await asyncio.sleep(_LIVE_PUSH_INTERVAL_S)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: %s", websocket.client)
    except Exception:
        logger.exception("Unexpected error in WebSocket handler")
        await websocket.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
