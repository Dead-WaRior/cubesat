"""Persistence layer for CubeSat tracks and alerts using SQLite."""

from __future__ import annotations

import json
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Any

from shared.schemas import TrackObject, RiskAlert

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent.parent / "cubesat.db"

class CubeSatDatabase:
    """Handles persistent storage of tracking and risk data."""

    def __init__(self, db_path: Path = _DB_PATH) -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    track_id INTEGER PRIMARY KEY,
                    data TEXT,
                    last_seen TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    track_id INTEGER,
                    alert_level TEXT,
                    data TEXT,
                    timestamp TIMESTAMP
                )
            """)
            conn.commit()

    def save_track(self, track: TrackObject) -> None:
        """Upsert a track object."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tracks (track_id, data, last_seen) VALUES (?, ?, ?)",
                (
                    track.track_id,
                    track.model_dump_json(),
                    track.last_seen.isoformat() if track.last_seen else None
                )
            )
            conn.commit()

    def save_alert(self, alert: RiskAlert) -> None:
        """Insert a risk alert."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO alerts (alert_id, track_id, alert_level, data, timestamp) VALUES (?, ?, ?, ?, ?)",
                (
                    alert.alert_id,
                    alert.track_id,
                    alert.alert_level.value,
                    alert.model_dump_json(),
                    alert.timestamp.isoformat()
                )
            )
            conn.commit()

    def get_active_tracks(self) -> List[dict]:
        """Retrieve tracks seen recently (within last 5 minutes)."""
        # Note: simplistic implementation for demo
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("SELECT data FROM tracks")
            rows = cursor.fetchall()
            return [json.loads(row[0]) for row in rows]

    def get_recent_alerts(self, limit: int = 50) -> List[dict]:
        """Retrieve recent alerts."""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM alerts ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [json.loads(row[0]) for row in rows]
