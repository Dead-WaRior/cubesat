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
from ingestion.database import CubeSatDatabase
from ingestion.worker import ProcessingWorker
from shared.schemas import ImageFrame, TelemetryPacket
from vision.pipeline import VisionPipeline
from prediction.pipeline import PredictionPipeline

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
# Global state & Worker
# ---------------------------------------------------------------------------

queue_manager: QueueManager = QueueManager()
db = CubeSatDatabase()

worker = ProcessingWorker(
    queue_manager=queue_manager,
    db=db,
    vision_pipeline=VisionPipeline(),
    prediction_pipeline=PredictionPipeline()
)

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
    worker.cache_telemetry(packet)
    logger.info("Received telemetry for frame %s", packet.frame_id)
    return {"frame_id": packet.frame_id, "received": True}


@app.get("/tracks", summary="List active tracks")
async def get_tracks() -> list[dict[str, Any]]:
    """Return all currently active object tracks."""
    return db.get_active_tracks()


@app.get("/alerts", summary="List recent risk alerts")
async def get_alerts() -> list[dict[str, Any]]:
    """Return recently generated collision risk alerts."""
    return db.get_recent_alerts()


# ---------------------------------------------------------------------------
# Background Processing
# ---------------------------------------------------------------------------

from firebase_admin import db as rtdb

async def push_to_rtdb() -> None:
    """Push live system state to Firebase Realtime Database at ~10 Hz."""
    logger.info("Started pushing live data to Firebase RTDB")
    
    # Needs to be initialized somewhere, assuming caller or top of file does it.
    try:
        ref = rtdb.reference('live')
        while True:
            payload: dict[str, Any] = {
                "frame": worker.latest_frame_processed,
                "tracks": worker.active_tracks,
                "alerts": [a.model_dump() for a in worker.recent_alerts],
                "sat_lla": getattr(worker, 'sat_lla', None),
                "sat_path": getattr(worker, 'sat_path', []),
                "sat_bus_stats": getattr(worker, 'sat_bus_stats', {}),
                "system_health": {
                    "simulation": "ok",
                    "ingestion": "ok",
                    "vision": "ok",
                    "prediction": "ok",
                },
                "timestamp": datetime.now(tz=timezone.utc).isoformat()
            }
            # Firebase Realtime DB does not support numpy types, json.dumps handles it 
            # so we'd better convert to dict primitives first, or json dump then load.
            json_payload = json.loads(json.dumps(payload, default=str))
            ref.set(json_payload)
            await asyncio.sleep(_LIVE_PUSH_INTERVAL_S)
    except Exception as e:
        logger.exception("Unexpected error in RTDB push loop: %s", e)

@app.on_event("startup")
async def startup_event():
    import firebase_admin
    if not firebase_admin._apps:
        # User needs to set GOOGLE_APPLICATION_CREDENTIALS and FIREBASE_DATABASE_URL
        # or it will pick up default credentials for emulator/default project.
        firebase_admin.initialize_app()
    asyncio.create_task(worker.run_forever())
    asyncio.create_task(push_to_rtdb())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
