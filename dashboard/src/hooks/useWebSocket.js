import { useEffect, useRef, useCallback } from 'react'
import useDashboardStore from '../store'

/** WebSocket endpoint – uses the Vite proxy in development */
const WS_URL = '/ws/live'

/** Delay in milliseconds before attempting a reconnection */
const RECONNECT_DELAY_MS = 2000

/**
 * useWebSocket
 *
 * Custom hook that maintains a live WebSocket connection to the CubeSat
 * backend.  On every inbound JSON message the relevant Zustand store
 * actions are called to keep the UI in sync.
 *
 * Expected server message shape (all fields optional):
 * ```json
 * {
 *   "frame":        "<base64 data URI>",
 *   "tracks":       [ { track_id, x, y, vx, vy, pc, alert_level, tca_min, age_frames, confidence, bbox } ],
 *   "alerts":       [ { alert_id, track_id, alert_level, pc, miss_distance_km, tca_min, recommended_action, timestamp } ],
 *   "system_health": { "simulation": "ok", "ingestion": "ok", "vision": "ok", "prediction": "ok" },
 *   "timestamp":    "<ISO 8601>"
 * }
 * ```
 *
 * @returns {{ isConnected: boolean }}
 */
function useWebSocket() {
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const isMountedRef = useRef(true)

  const setFrame = useDashboardStore((s) => s.setFrame)
  const setTracks = useDashboardStore((s) => s.setTracks)
  const setAlerts = useDashboardStore((s) => s.setAlerts)
  const addAlert = useDashboardStore((s) => s.addAlert)
  const setSystemHealth = useDashboardStore((s) => s.setSystemHealth)
  const setConnected = useDashboardStore((s) => s.setConnected)
  const updatePcHistory = useDashboardStore((s) => s.updatePcHistory)
  const setLastUpdate = useDashboardStore((s) => s.setLastUpdate)
  const setSatLla = useDashboardStore((s) => s.setSatLla)
  const setSatPath = useDashboardStore((s) => s.setSatPath)
  const setSatBusStats = useDashboardStore((s) => s.setSatBusStats)
  const isConnected = useDashboardStore((s) => s.isConnected)

  const connect = useCallback(() => {
    if (!isMountedRef.current) return

    // Use location.host which includes the port (e.g. localhost:3000)
    // The Vite proxy in vite.config.js will redirect /ws/live to localhost:8000
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}${WS_URL}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (!isMountedRef.current) return
      setConnected(true)
    }

    ws.onclose = () => {
      if (!isMountedRef.current) return
      setConnected(false)
      // Schedule reconnect
      reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS)
    }

    ws.onerror = () => {
      // onclose fires after onerror, so reconnect is handled there
      ws.close()
    }

    ws.onmessage = (event) => {
      if (!isMountedRef.current) return

      let data
      try {
        data = JSON.parse(event.data)
      } catch {
        // Silently ignore malformed messages
        return
      }

      if (data.frame !== undefined) setFrame(data.frame)

      if (Array.isArray(data.tracks)) {
        // Normalize alert_level to lowercase for consistent frontend usage
        const normalizedTracks = data.tracks.map(t => ({
          ...t,
          alert_level: (t.alert_level || 'nominal').toLowerCase()
        }))
        setTracks(normalizedTracks)
        // Record Pc history for each track
        const now = Date.now() / 1000
        normalizedTracks.forEach((t) => {
          if (typeof t.pc === 'number') {
            updatePcHistory(t.track_id, t.pc, now)
          }
        })
      }

      if (Array.isArray(data.alerts)) {
        // Normalize alert_level to lowercase
        const normalizedAlerts = data.alerts.map(a => ({
          ...a,
          alert_level: (a.alert_level || '').toLowerCase(),
          // Map backend field names to frontend expected names
          pc: a.probability_of_collision ?? a.pc,
          tca_min: a.time_to_closest_approach != null ? a.time_to_closest_approach / 60 : a.tca_min,
        }))
        setAlerts(normalizedAlerts)
      }

      if (data.alert) {
        // Single new alert pushed from server (normalize)
        const normalized = {
          ...data.alert,
          alert_level: (data.alert.alert_level || '').toLowerCase(),
          pc: data.alert.probability_of_collision ?? data.alert.pc,
          tca_min: data.alert.time_to_closest_approach != null ? data.alert.time_to_closest_approach / 60 : data.alert.tca_min,
        }
        addAlert(normalized)
      }

      if (data.system_health) {
        setSystemHealth(data.system_health)
      }

      if (data.timestamp) {
        setLastUpdate(data.timestamp)
      }

      if (data.sat_lla) {
        setSatLla(data.sat_lla)
      }

      if (data.sat_path) {
        setSatPath(data.sat_path)
      }

      if (data.sat_bus_stats) {
        setSatBusStats(data.sat_bus_stats)
      }
    }
  }, [
    setFrame,
    setTracks,
    setAlerts,
    addAlert,
    setSystemHealth,
    setConnected,
    updatePcHistory,
    setLastUpdate,
    setSatLla,
    setSatPath,
    setSatBusStats,
  ])

  useEffect(() => {
    isMountedRef.current = true
    connect()

    return () => {
      isMountedRef.current = false
      clearTimeout(reconnectTimerRef.current)
      if (wsRef.current) {
        // Remove onclose before closing so we don't schedule a reconnect
        wsRef.current.onclose = null
        wsRef.current.close()
      }
      setConnected(false)
    }
    // connect is wrapped in useCallback so it has a stable reference;
    // the empty array is intentional — we only want to open the socket once.
  }, [])

  return { isConnected }
}

export default useWebSocket
