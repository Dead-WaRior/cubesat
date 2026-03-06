import { create } from 'zustand'

/**
 * @typedef {Object} Track
 * @property {string} track_id - Unique identifier for the debris track
 * @property {number} x - X position in frame (0-1 normalised)
 * @property {number} y - Y position in frame (0-1 normalised)
 * @property {number} vx - X velocity component (m/s)
 * @property {number} vy - Y velocity component (m/s)
 * @property {number} pc - Probability of collision (0-1)
 * @property {string} alert_level - 'advisory' | 'warning' | 'critical'
 * @property {number} tca_min - Time to closest approach in minutes
 * @property {number} age_frames - Number of frames the track has been active
 * @property {number} confidence - Detection confidence (0-1)
 * @property {Object} bbox - Bounding box {x, y, w, h} in pixel coords
 */

/**
 * @typedef {Object} Alert
 * @property {string} alert_id - Unique identifier for the alert
 * @property {string} track_id - Associated track ID
 * @property {string} alert_level - 'advisory' | 'warning' | 'critical'
 * @property {number} pc - Probability of collision at time of alert
 * @property {number} miss_distance_km - Predicted miss distance in kilometres
 * @property {number} tca_min - Time to closest approach in minutes
 * @property {string} recommended_action - Human-readable action string
 * @property {string} timestamp - ISO 8601 timestamp
 * @property {boolean} acknowledged - Whether the alert has been acknowledged
 */

/**
 * @typedef {Object} SystemHealth
 * @property {'ok'|'degraded'|'error'|'unknown'} simulation - Simulation subsystem status
 * @property {'ok'|'degraded'|'error'|'unknown'} ingestion - Ingestion subsystem status
 * @property {'ok'|'degraded'|'error'|'unknown'} vision - Vision subsystem status
 * @property {'ok'|'degraded'|'error'|'unknown'} prediction - Prediction subsystem status
 */

/**
 * @typedef {Object} PcDataPoint
 * @property {number} timestamp - Unix epoch seconds
 * @property {number} pc - Probability of collision
 */

/**
 * @typedef {Object} DashboardState
 * @property {string|null} frame - Base64-encoded latest camera frame (data URI)
 * @property {Track[]} tracks - Currently active debris tracks
 * @property {Alert[]} alerts - Recent alerts (capped at 50)
 * @property {SystemHealth} systemHealth - Health of each subsystem
 * @property {boolean} isConnected - Whether the WebSocket is connected
 * @property {Object.<string, PcDataPoint[]>} pcHistory - Per-track Pc history (last 30 s)
 * @property {string|null} lastUpdate - ISO timestamp of the most recent message
 */

/**
 * Global Zustand store for the CubeSat Collision Prediction Dashboard.
 *
 * All WebSocket data flows into this store; UI components subscribe to
 * only the slices they need to minimise unnecessary re-renders.
 */
const useDashboardStore = create((set) => ({
  /** @type {string|null} */
  frame: null,

  /** @type {Track[]} */
  tracks: [],

  /** @type {Alert[]} */
  alerts: [],

  /** @type {SystemHealth} */
  systemHealth: {
    simulation: 'unknown',
    ingestion: 'unknown',
    vision: 'unknown',
    prediction: 'unknown',
  },

  /** @type {boolean} */
  isConnected: false,

  /** @type {Object.<string, PcDataPoint[]>} */
  pcHistory: {},

  /** @type {string|null} */
  lastUpdate: null,

  // ── Actions ────────────────────────────────────────────────────────────────

  /**
   * Replace the current camera frame.
   * @param {string|null} frame - Base64 data URI or null
   */
  setFrame: (frame) => set({ frame }),

  /**
   * Replace the full list of active tracks.
   * @param {Track[]} tracks
   */
  setTracks: (tracks) => set({ tracks }),

  /**
   * Replace the full alert list (trimmed to last 50 entries).
   * @param {Alert[]} alerts
   */
  setAlerts: (alerts) =>
    set({ alerts: alerts.slice(-50).map((a) => ({ acknowledged: false, ...a })) }),

  /**
   * Merge updated subsystem health values into current state.
   * @param {Partial<SystemHealth>} health
   */
  setSystemHealth: (health) =>
    set((state) => ({ systemHealth: { ...state.systemHealth, ...health } })),

  /**
   * Set WebSocket connection status.
   * @param {boolean} connected
   */
  setConnected: (connected) => set({ isConnected: connected }),

  /**
   * Append a single new alert.  Keeps only the most recent 50 alerts.
   * @param {Alert} alert
   */
  addAlert: (alert) =>
    set((state) => ({
      alerts: [...state.alerts, { acknowledged: false, ...alert }].slice(-50),
    })),

  /**
   * Record a new Pc data point for a track.
   * Retains only data points from the last 30 seconds.
   * @param {string} trackId - The track identifier
   * @param {number} pc - The current probability of collision
   * @param {number} [timestamp] - Unix epoch seconds (defaults to now)
   */
  updatePcHistory: (trackId, pc, timestamp) => {
    const now = timestamp ?? Date.now() / 1000
    const cutoff = now - 30

    set((state) => {
      const existing = state.pcHistory[trackId] ?? []
      const updated = [...existing.filter((p) => p.timestamp >= cutoff), { timestamp: now, pc }]
      return { pcHistory: { ...state.pcHistory, [trackId]: updated } }
    })
  },

  /**
   * Mark an alert as acknowledged so the critical modal is dismissed.
   * @param {string} alertId - The alert_id to acknowledge
   */
  acknowledgeAlert: (alertId) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.alert_id === alertId ? { ...a, acknowledged: true } : a,
      ),
    })),

  /**
   * Store the ISO timestamp of the most recent inbound message.
   * @param {string} ts
   */
  setLastUpdate: (ts) => set({ lastUpdate: ts }),
}))

export default useDashboardStore
