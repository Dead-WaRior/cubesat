# Welcome to Cloud Functions for Firebase for Python!
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore
from flask import Flask, jsonify
from flask_cors import CORS
import math
import logging

initialize_app()
db = firestore.client()

app = Flask(__name__)
# Enable CORS for all routes (configured for production ideally)
CORS(app)

logger = logging.getLogger(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "timestamp": "now"})

@app.route('/tracks', methods=['GET'])
def get_tracks():
    """Return all currently active object tracks from Firestore."""
    try:
        docs = db.collection('tracks').limit(100).stream()
        return jsonify([doc.to_dict() for doc in docs])
    except Exception as e:
        logger.error(f"Error fetching tracks: {e}")
        return jsonify([]), 500

@app.route('/alerts', methods=['GET'])
def get_alerts():
    """Return recently generated collision risk alerts from Firestore."""
    try:
        docs = db.collection('alerts').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(50).stream()
        return jsonify([doc.to_dict() for doc in docs])
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return jsonify([]), 500

# Expose the Flask app as a Firebase Cloud Function HTTP endpoint
@https_fn.on_request()
def api(req: https_fn.Request) -> https_fn.Response:
    # Use Flask's testing machinery to handle the request from Firebase
    with app.request_context(req.environ):
        return app.full_dispatch_request()
