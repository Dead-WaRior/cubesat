"""Modular background processor for CubeSat imagery and telemetry."""

import asyncio
import base64
import logging
import cv2
import numpy as np
import math
from typing import Optional, List, Dict, Any

from ingestion.queue_manager import QueueManager
from ingestion.database import CubeSatDatabase
from shared.schemas import ImageFrame, TelemetryPacket, RiskAlert, TrackObject
from vision.pipeline import VisionPipeline
from prediction.pipeline import PredictionPipeline

logger = logging.getLogger(__name__)

class ProcessingWorker:
    """Orchestrates the asynchronous processing of imagery and telemetry."""

    def __init__(
        self,
        queue_manager: QueueManager,
        db: CubeSatDatabase,
        vision_pipeline: VisionPipeline,
        prediction_pipeline: PredictionPipeline,
    ) -> None:
        self.queue_manager = queue_manager
        self.db = db
        self.vision_pipeline = vision_pipeline
        self.prediction_pipeline = prediction_pipeline
        
        self.latest_frame_processed: Optional[str] = None
        self.active_tracks: List[Dict[str, Any]] = []
        self.recent_alerts: List[RiskAlert] = []
        
        # Sync buffer
        self._telemetry_cache: Dict[int, TelemetryPacket] = {}
        self._max_cache_size = 50
        
        self.sat_lla = None
        self.sat_path = []
        self.sat_bus_stats = {
            "battery_v": 12.4,
            "cpu_temp": 42.5,
            "wheel_rpm": 1200,
            "load_pct": 24.1
        }

    async def run_forever(self):
        """Main processing loop."""
        logger.info("Processing worker started.")
        while True:
            frame_data: ImageFrame = self.queue_manager.dequeue()
            if frame_data:
                await self._process_single_frame(frame_data)
            await asyncio.sleep(0.01)

    def cache_telemetry(self, packet: TelemetryPacket):
        """Store telemetry in buffer for sync with future frames."""
        self._telemetry_cache[packet.frame_id] = packet
        if len(self._telemetry_cache) > self._max_cache_size:
            # Drop oldest key
            oldest = min(self._telemetry_cache.keys())
            del self._telemetry_cache[oldest]

    async def _process_single_frame(self, frame_data: ImageFrame):
        """Process a frame through vision and prediction."""
        try:
            # 1. Decode
            img_bytes = base64.b64decode(frame_data.image_data)
            img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_arr, cv2.IMREAD_GRAYSCALE)
            
            # 2. Vision Pipeline
            det_events, tracks = self.vision_pipeline.process_frame(
                img, frame_data.frame_id, frame_data.timestamp
            )
            
            # 3. Synchronized Prediction
            telemetry = self._telemetry_cache.get(frame_data.frame_id)
            if telemetry:
                # Synchronized match found
                tracks_with_bbox = []
                for t in tracks:
                    matching_event = next((e for e in det_events if e.track_id == t["track_id"]), None)
                    if matching_event:
                        t["bbox"] = matching_event.bbox
                        tracks_with_bbox.append(t)
                
                alerts = self.prediction_pipeline.process_tracks(tracks_with_bbox, telemetry)
                for alert in alerts:
                    self.db.save_alert(alert)
                
                # Cleanup cache up to this frame
                keys_to_del = [k for k in self._telemetry_cache.keys() if k <= frame_data.frame_id]
                for k in keys_to_del:
                    del self._telemetry_cache[k]

            # 4. Annotate and Buffer for UI
            annotated = self.vision_pipeline.annotate_frame(img, tracks)
            _, buf = cv2.imencode(".png", annotated)
            self.latest_frame_processed = f"data:image/png;base64,{base64.b64encode(buf).decode('ascii')}"
            
            # 5. Persistence
            for t in tracks:
                track_obj = TrackObject(
                    track_id=t["track_id"],
                    last_seen=frame_data.timestamp,
                    is_active=True
                )
                self.db.save_track(track_obj)
            
            self.active_tracks = tracks
            self.recent_alerts = [RiskAlert.model_validate(a) for a in self.db.get_recent_alerts(limit=10)]

            # 6. Advanced Situational Awareness (3D Paths & Bus Stats)
            if telemetry:
                pos = telemetry.satellite_position
                vel = telemetry.velocity
                sat_state = np.array([pos['x'], pos['y'], pos['z'], vel['vx'], vel['vy'], vel['vz']])
                
                # Satellite Path
                self.sat_path = self.prediction_pipeline.get_sat_prediction_path(sat_state)
                
                # Track Paths
                for t in self.active_tracks:
                    t["prediction_path"] = self.prediction_pipeline.get_prediction_path(t["track_id"])

                # Sub-satellite point
                r = math.sqrt(pos['x']**2 + pos['y']**2 + pos['z']**2)
                
                # Prevent math domain error due to floating point inaccuracies
                z_over_r = max(-1.0, min(1.0, pos['z'] / r))
                lat = math.degrees(math.asin(z_over_r))
                lon = math.degrees(math.atan2(pos['y'], pos['x']))
                self.sat_lla = {"lat": lat, "lon": lon, "alt": r - 6371.0}

                # Simulate Bus Stats jitter
                import random
                self.sat_bus_stats = {
                    "battery_v": round(12.2 + random.uniform(0, 0.4), 2),
                    "cpu_temp": round(40.0 + random.uniform(0, 8.0), 1),
                    "wheel_rpm": int(1100 + random.uniform(0, 300)),
                    "load_pct": round(20.0 + random.uniform(0, 15.0), 1)
                }

        except Exception as e:
            logger.exception("Worker error processing frame %s: %s", frame_data.frame_id, e)
