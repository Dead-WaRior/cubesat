import { useEffect, useRef, useCallback } from 'react'
import useDashboardStore from '../store'
import { database } from '../firebase'
import { ref, onValue, off } from "firebase/database"

/**
 * useWebSocket (now useFirebaseDatabase)
 *
 * Custom hook that maintains a live connection to the CubeSat Firebase Realtime Database.
 * On every inbound JSON message the relevant Zustand store actions are called to keep the UI in sync.
 *
 * Expected server message shape is the same as before, but read from Firebase Realtime Database.
 */
function useWebSocket() {
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

    setConnected(true)

    const liveDataRef = ref(database, 'live')
    
    // Listen to changes in the 'live' node
    onValue(liveDataRef, (snapshot) => {
      if (!isMountedRef.current) return
      
      const data = snapshot.val()
      if (!data) return

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
    }, (error) => {
        console.error("Firebase DB Error", error)
        setConnected(false)
    })
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
      const liveDataRef = ref(database, 'live')
      off(liveDataRef)
      setConnected(false)
    }
  }, [connect])

  return { isConnected }
}

export default useWebSocket
