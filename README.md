# 🛰️ CubeSat AI-Based Real-Time Collision Prediction System

A ground-based software platform that processes satellite camera imagery and telemetry data, detects nearby space debris, and predicts collision risks near real time. The system uses a simulation layer that generates realistic synthetic orbital imagery and debris scenarios since live satellite feeds  not available during development.

## Architecture Overview — 5-Layer Pipeline

| Layer | Name | Responsibility | Technology |
|-------|------|----------------|-----------|
| 1 | Simulation Engine | Synthetic orbital imagery and debris movement | Python, OpenCV, NumPy |
| 2 | Data Ingestion | Receives frames & telemetry, queues for processing, persists tracks & alerts | FastAPI, Redis, SQLite |
| 3 | Vision & Tracking | Detects debris, tracks across time with object IDs | OpenCV, YOLOv8-nano, SORT |
| 4 | Prediction & Risk | Predicts trajectories, computes Pc, plans avoidance maneuvers | NumPy, SciPy, filterpy UKF, astropy |
| 5 | Dashboard & Alerts | Real-time 3D orbital display, risk scores, ground track, operator alerts | React, Three.js, WebSocket, Recharts |

**Data Flow:** `Simulation → Redis Queue → Detector → Tracker → Predictor → Risk Scorer → Dashboard`

## Repository Structure

```
cubesat/
├── simulation/              # Layer 1: Simulation Engine
│   ├── engine.py            # Main simulation engine
│   ├── star_field.py        # Static star field generator
│   ├── debris.py            # Debris object models and animation
│   ├── noise.py             # Noise generation (hot pixels, Gaussian, cosmic rays)
│   ├── telemetry.py         # TelemetryPacket generator
│   ├── config.py            # YAML config loader
│   ├── run.py               # Standalone runner
│   └── scenarios/           # Built-in scenarios
│       ├── safe_flyby.yaml
│       ├── close_approach.yaml
│       └── critical_conjunction.yaml
├── ingestion/               # Layer 2: Data Ingestion
│   ├── api.py               # FastAPI app (/health, /ws/live, REST endpoints)
│   ├── redis_client.py      # Redis stream producer/consumer
│   ├── queue_manager.py     # Frame-drop policy (max 30 frames)
│   ├── database.py          # SQLite persistence layer (tracks & alerts)
│   └── worker.py            # Async processing worker (vision → prediction loop)
├── vision/                  # Layer 3: Detection & Tracking
│   ├── preprocessing.py     # Dark subtraction, CLAHE, hot-pixel correction
│   ├── streak_detector.py   # Canny + Hough Line streak detection
│   ├── object_detector.py   # YOLOv8-nano wrapper with blob fallback
│   ├── detector.py          # Two-stage merged detection pipeline
│   ├── sort_tracker.py      # SORT multi-object tracker with Kalman internals
│   ├── pipeline.py          # Full vision pipeline orchestrator
│   └── yolo_config.yaml     # YOLOv8 training configuration
├── prediction/              # Layer 4: Trajectory & Risk
│   ├── coordinate_transform.py  # Pixel to ECI coordinate conversion
│   ├── orbital_dynamics.py      # J2, drag, SRP perturbation models (RK4)
│   ├── ukf_tracker.py           # UKF with 6-state [x,y,z,vx,vy,vz]
│   ├── closest_approach.py      # TCA computation
│   ├── collision_probability.py # Alfriend-Akella Pc calculation
│   ├── risk_assessor.py         # ADVISORY/WARNING/CRITICAL tier classification
│   ├── maneuver_planner.py      # Impulsive burn planner for collision avoidance
│   └── pipeline.py              # Full prediction pipeline orchestrator
├── dashboard/               # Layer 5: React Frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── store.js         # Zustand state management
│   │   ├── hooks/useWebSocket.js
│   │   └── components/
│   │       ├── LiveFeed.jsx          # Live camera feed with overlay
│   │       ├── OrbitalView.jsx       # 3D orbital scene (Three.js / R3F)
│   │       ├── GroundTrack.jsx       # 2D sub-satellite point on world map
│   │       ├── TracksTable.jsx       # Active debris tracks table
│   │       ├── ObjectInspector.jsx   # Sliding sidebar for track deep-dive
│   │       ├── RiskAnalytics.jsx     # Pc history chart for selected track
│   │       ├── RiskTimeline.jsx      # Timeline of risk alert events
│   │       ├── AlertFeed.jsx         # Live alert feed
│   │       ├── ManeuverPanel.jsx     # Recommended avoidance maneuver display
│   │       ├── SystemHealth.jsx      # Subsystem health indicators
│   │       ├── SystemMetricsHUD.jsx  # Top-level mission statistics HUD
│   │       └── CriticalModal.jsx     # Full-screen critical alert overlay
│   ├── package.json
│   └── Dockerfile
├── shared/                  # Pydantic data schemas
│   └── schemas.py           # TelemetryPacket, ImageFrame, DetectionEvent, TrackObject, RiskAlert
├── tests/                   # 60 unit & integration tests
├── notebooks/               # Jupyter prototyping notebooks
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── cubesat.db               # SQLite database (auto-created at runtime)
└── requirements.txt
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### Run with Docker Compose mac/linux

```bash
# Start all services
make start

# View logs
docker compose logs -f

# Stop all services
make stop
```

Services available at:
- **Backend API**: http://localhost:8000
- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

### Local Development

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the FastAPI backend
uvicorn ingestion.api:app --host 0.0.0.0 --port 8000 --reload

# In another terminal, run the simulation
python simulation/run.py --scenario safe_flyby --frames 100

# Run the React dashboard
cd dashboard
npm install
npm run dev
```

## Simulation Scenarios

Three built-in scenarios are available:

| Scenario | Description | Expected Outcome |
|----------|-------------|-----------------|
| `safe_flyby` | Debris passes at >20 km distance | No WARNING+ alerts |
| `close_approach` | Debris closes from 15 km to 2 km | ADVISORY at 10 km, WARNING at 5 km |
| `critical_conjunction` | Three-object conjunction, TCA in 12 min | CRITICAL alert fires |

```bash
# Run a specific scenario
python simulation/run.py --scenario critical_conjunction --frames 200

# Save frames to disk
python simulation/run.py --scenario close_approach --frames 100 --output-dir /tmp/frames

# Push to Redis (requires running Redis)
python simulation/run.py --scenario safe_flyby --redis
```

## Alert Tier System

| Level | Condition | Color | Action |
|-------|-----------|-------|--------|
| ADVISORY | Pc > 1e-5 or range < 10 km | 🟡 Yellow | Monitoring frequency increased |
| WARNING | Pc > 1e-4 or range < 5 km | 🟠 Orange | Operator reviews maneuver recommendation |
| CRITICAL | Pc > 1e-3 or TCA < 15 min | 🔴 Red | Immediate action required |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/frames` | Submit an image frame |
| POST | `/telemetry` | Submit a telemetry packet |
| GET | `/tracks` | List active debris tracks |
| GET | `/alerts` | List recent alerts |
| WS | `/ws/live` | Live data stream (100ms updates) |

## Testing

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ -v --tb=short

# Run specific test file
pytest tests/test_prediction.py -v
```

60 tests cover all modules including:
- Pydantic schema validation
- Simulation frame generation
- Image preprocessing pipeline
- Debris detection & SORT tracking
- UKF trajectory prediction
- Collision probability calculation
- Risk alert tier classification
- Integration scenarios (safe flyby, close approach, critical conjunction)

## Linting

```bash
make lint
# or
ruff check . --exclude dashboard
```

## Key Design Decisions

1. **Simulation-first**: The simulation layer is the ONLY component that needs replacement for real satellite data. All downstream modules consume standardized Pydantic schemas.

2. **Graceful degradation**: Redis, YOLOv8, and other optional dependencies have fallbacks. The system works without them for testing.

3. **UKF with perturbations**: The Unscented Kalman Filter includes J2 oblateness, atmospheric drag, and solar radiation pressure for realistic LEO orbital mechanics.

4. **Alfriend-Akella Pc**: Collision probability uses the standard 2D projection method used by US Space Command.

5. **SORT tracking**: Multi-object tracking requires 4+ consecutive frame confirmations before promoting a track to "active" to suppress false positives.

6. **Impulsive maneuver planner**: When a CRITICAL alert fires, `maneuver_planner.py` evaluates candidate in-track and radial burns at a configurable lead time before TCA and recommends the minimum delta-v burn that achieves the target miss distance.

7. **SQLite persistence**: `database.py` provides a lightweight persistence layer for tracks and alerts so that history survives backend restarts without requiring a separate database service.

8. **3D orbital visualisation**: `OrbitalView.jsx` uses React Three Fiber and Three.js to render a real-time 3D scene with the satellite globe, debris objects, and predicted trajectory paths.

## Dependencies

### Python Backend
- `fastapi` + `uvicorn` — REST API and WebSocket server
- `opencv-python-headless` — Image processing
- `filterpy` — Kalman and Unscented Kalman filters
- `numpy` + `scipy` — Scientific computing
- `astropy` — Coordinate transforms and orbital mechanics
- `pydantic` + `pydantic-settings` — Data validation and schemas
- `redis` — Stream-based message queue
- `ultralytics` — YOLOv8 (optional, blob detection fallback available)

### React Frontend
- `react` 18 + `vite` — UI framework and build tool
- `three` + `@react-three/fiber` + `@react-three/drei` — 3D orbital visualisation
- `recharts` — Time-series charts for Pc history
- `zustand` — Lightweight state management
- `tailwindcss` — Utility-first styling

## License

MIT
