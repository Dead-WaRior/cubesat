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
  const isConnected = useDashboardStore((s) => s.isConnected)

  const connect = useCallback(() => {
    if (!isMountedRef.current) return

    // Build an absolute ws(s):// URL so it works outside the Vite proxy too
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
        setTracks(data.tracks)
        // Record Pc history for each track
        const now = Date.now() / 1000
        data.tracks.forEach((t) => {
          if (typeof t.pc === 'number') {
            updatePcHistory(t.track_id, t.pc, now)
          }
        })
      }

      if (Array.isArray(data.alerts)) {
        // If the server sends the full alert list, replace it
        setAlerts(data.alerts)
      }

      if (data.alert) {
        // Single new alert pushed from server
        addAlert(data.alert)
      }

      if (data.system_health) {
        setSystemHealth(data.system_health)
      }

      if (data.timestamp) {
        setLastUpdate(data.timestamp)
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
