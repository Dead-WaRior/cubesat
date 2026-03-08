"""Persistence layer for CubeSat tracks and alerts using Firestore."""

from __future__ import annotations

import logging
from typing import List

from firebase_admin import firestore
from shared.schemas import TrackObject, RiskAlert

logger = logging.getLogger(__name__)

class CubeSatDatabase:
    """Handles persistent storage of tracking and risk data in Firestore."""

    def __init__(self) -> None:
        self.db = firestore.client()

    def save_track(self, track: TrackObject) -> None:
        """Upsert a track object."""
        try:
            doc_ref = self.db.collection('tracks').document(str(track.track_id))
            doc_ref.set(track.model_dump())
        except Exception as e:
            logger.error(f"Error saving track down to Firestore: {e}")

    def save_alert(self, alert: RiskAlert) -> None:
        """Insert a risk alert."""
        try:
            doc_ref = self.db.collection('alerts').document(alert.alert_id)
            doc_ref.set(alert.model_dump(), merge=True)
        except Exception as e:
            logger.error(f"Error saving alert down to Firestore: {e}")

    def get_active_tracks(self) -> List[dict]:
        """Retrieve tracks seen recently (within last 5 minutes)."""
        try:
            docs = self.db.collection('tracks').limit(100).stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error retrieving tracks from Firestore: {e}")
            return []

    def get_recent_alerts(self, limit: int = 50) -> List[dict]:
        """Retrieve recent alerts."""
        try:
            docs = self.db.collection('alerts').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error retrieving alerts from Firestore: {e}")
            return []
