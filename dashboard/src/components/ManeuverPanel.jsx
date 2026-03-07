import { useState, useEffect, useCallback } from 'react'
import useDashboardStore from '../store'

/**
 * Derive delta-V recommendations from the most severe active alert.
 */
function buildRecommendations(alert) {
  if (!alert) return []
  const recs = []
  if (alert.recommended_action) recs.push(alert.recommended_action)

  const level = (alert.alert_level || '').toLowerCase()
  if (level === 'critical') {
    recs.push({
      action: 'Execute emergency avoidance burn',
      timeToManeuver: Math.max(0, ((alert.tca_min || 0) * 60) - 120),
      deltaV: 1.25,
      orbitShift: 840
    })
  } else if (level === 'warning') {
    recs.push({
      action: 'Minor Thruster Burn (Precautionary)',
      timeToManeuver: Math.max(0, ((alert.tca_min || 0) * 60) - 300),
      deltaV: 0.15,
      orbitShift: 420
    })
  }
  return recs
}

/**
 * ManeuverPanel
 *
 * Two modes:
 *  - MANUAL: operator clicks to approve/simulate maneuver
 *  - AUTO:   system automatically executes avoidance when Pc crosses critical threshold
 */
function ManeuverPanel() {
  const alerts = useDashboardStore((s) => s.alerts)
  const acknowledgeAlert = useDashboardStore((s) => s.acknowledgeAlert)
  const isSimulating = useDashboardStore((s) => s.isSimulating)
  const setIsSimulating = useDashboardStore((s) => s.setIsSimulating)
  const setHypotheticalPath = useDashboardStore((s) => s.setHypotheticalPath)
  const satPath = useDashboardStore((s) => s.satPath)
  const tracks = useDashboardStore((s) => s.tracks)

  const [maneuverMode, setManeuverMode] = useState('manual') // 'manual' | 'auto'
  const [autoExecuted, setAutoExecuted] = useState(false)

  const executeManeuver = useCallback(() => {
    if (isSimulating) return
    const safetyPath = satPath.map(p => ({
      x: p.x * 1.05,
      y: p.y * 1.05,
      z: p.z * 1.05
    }))
    setHypotheticalPath(safetyPath)
    setIsSimulating(true)
    alerts.forEach(a => acknowledgeAlert(a.alert_id))
  }, [isSimulating, satPath, setHypotheticalPath, setIsSimulating, alerts, acknowledgeAlert])

  const stopSimulation = useCallback(() => {
    setIsSimulating(false)
    setAutoExecuted(false)
  }, [setIsSimulating])

  // AUTO MODE: detect critical tracks and auto-execute
  const hasCriticalTrack = tracks.some(t => (t.alert_level || '').toLowerCase() === 'critical')

  useEffect(() => {
    if (maneuverMode === 'auto' && hasCriticalTrack && !isSimulating && !autoExecuted) {
      // Auto-execute maneuver after a brief delay
      const timer = setTimeout(() => {
        executeManeuver()
        setAutoExecuted(true)
      }, 1500)
      return () => clearTimeout(timer)
    }
  }, [maneuverMode, hasCriticalTrack, isSimulating, autoExecuted, executeManeuver])

  // Reset autoExecuted when no more critical tracks
  useEffect(() => {
    if (!hasCriticalTrack && autoExecuted) {
      setAutoExecuted(false)
    }
  }, [hasCriticalTrack, autoExecuted])

  // Find urgent alert for display
  const urgentAlert = alerts
    .filter((a) => {
      const lvl = (a.alert_level || '').toLowerCase()
      return !a.acknowledged && (lvl === 'warning' || lvl === 'critical')
    })
    .sort((a, b) => {
      const rank = { critical: 2, warning: 1 }
      return (rank[(b.alert_level || '').toLowerCase()] ?? 0) - (rank[(a.alert_level || '').toLowerCase()] ?? 0)
    })[0]

  const recommendations = buildRecommendations(urgentAlert)
  const isCritical = (urgentAlert?.alert_level || '').toLowerCase() === 'critical'

  return (
    <div className="glass-card rounded-xl overflow-hidden shadow-lg">
      {/* Header with Mode Toggle */}
      <div className="glass-header flex justify-between items-center">
        <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">
          {isSimulating ? '🔥 ' : ''}Maneuver Control
        </h2>
        <div className="flex items-center gap-1 bg-black/30 rounded-lg p-0.5">
          <button
            onClick={() => setManeuverMode('manual')}
            className={`text-[9px] font-bold uppercase px-2 py-1 rounded-md transition-all ${maneuverMode === 'manual'
                ? 'bg-blue-600 text-white shadow-[0_0_8px_rgba(59,130,246,0.3)]'
                : 'text-gray-500 hover:text-gray-300'
              }`}
          >
            Manual
          </button>
          <button
            onClick={() => setManeuverMode('auto')}
            className={`text-[9px] font-bold uppercase px-2 py-1 rounded-md transition-all ${maneuverMode === 'auto'
                ? 'bg-green-600 text-white shadow-[0_0_8px_rgba(34,197,94,0.3)]'
                : 'text-gray-500 hover:text-gray-300'
              }`}
          >
            Auto
          </button>
        </div>
      </div>

      {/* Auto mode indicator */}
      {maneuverMode === 'auto' && (
        <div className="px-4 py-2 bg-green-950/30 border-b border-green-800/30 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-[10px] text-green-400 font-bold uppercase tracking-wider">
            Autonomous Avoidance Active
          </span>
          <span className="text-[9px] text-green-500/60 ml-auto font-mono">
            AUTO-EXECUTE ON CRITICAL
          </span>
        </div>
      )}

      {/* Simulation Active State */}
      {isSimulating && (
        <div className="px-4 py-3 bg-blue-950/30 border-b border-blue-700/30">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse shadow-[0_0_6px_#38bdf8]" />
            <span className="text-[10px] text-blue-400 font-black uppercase tracking-widest">
              {maneuverMode === 'auto' ? 'AUTO-MANEUVER EXECUTING' : 'MANEUVER SIMULATING'}
            </span>
          </div>
          <div className="w-full bg-blue-950 rounded-full h-1.5 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full animate-[progress_3s_ease-in-out_infinite]"
              style={{ width: '100%', transformOrigin: 'left' }} />
          </div>
          <div className="flex justify-between mt-2 text-[9px] font-mono">
            <span className="text-green-400">THRUSTER IGNITION ✓</span>
            <span className="text-blue-300">ΔV: +1.25 m/s</span>
          </div>
          <button
            onClick={stopSimulation}
            className="w-full mt-2 text-[9px] font-bold uppercase py-1.5 rounded border border-gray-700 text-gray-400 hover:bg-white/5 transition-colors"
          >
            Cancel Maneuver
          </button>
        </div>
      )}

      {/* Alert Details (when not simulating) */}
      {!isSimulating && urgentAlert && (
        <div className="px-4 py-3 space-y-2">
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${isCritical ? 'bg-red-950/30 border-red-600/50' : 'bg-orange-950/30 border-orange-600/50'
            }`}>
            <span className="text-sm">{isCritical ? '🚨' : '⚠️'}</span>
            <div className="flex-1">
              <span className="text-xs font-bold text-gray-200">Track {urgentAlert.track_id}</span>
              {typeof urgentAlert.tca_min === 'number' && (
                <span className="text-[10px] text-gray-400 ml-2">TCA: {urgentAlert.tca_min.toFixed(1)} min</span>
              )}
            </div>
            <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${isCritical ? 'bg-red-600 text-white' : 'bg-orange-500 text-white'
              }`}>
              {urgentAlert.alert_level}
            </span>
          </div>

          {/* Recommendation details */}
          {recommendations.length > 0 && recommendations[recommendations.length - 1]?.action && (
            <div className="space-y-1 text-[10px] text-gray-400">
              <div className="flex justify-between">
                <span>Recommended:</span>
                <span className={`font-bold ${isCritical ? 'text-red-400' : 'text-orange-400'}`}>
                  {recommendations[recommendations.length - 1].action}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Delta-V:</span>
                <span className="font-mono text-white">{recommendations[recommendations.length - 1].deltaV?.toFixed(2)} m/s</span>
              </div>
              <div className="flex justify-between">
                <span>Orbit Shift:</span>
                <span className="font-mono text-white">+{recommendations[recommendations.length - 1].orbitShift} m</span>
              </div>
            </div>
          )}

          {/* Manual mode buttons */}
          {maneuverMode === 'manual' && (
            <div className="flex gap-2 pt-1">
              <button
                onClick={executeManeuver}
                className="flex-1 bg-green-600 hover:bg-green-500 active:bg-green-700 text-white text-[10px] font-bold py-2 px-3 rounded-lg transition-colors uppercase tracking-wider"
              >
                Execute Maneuver
              </button>
              <button
                onClick={() => acknowledgeAlert(urgentAlert.alert_id)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 text-[10px] font-bold py-2 px-3 rounded-lg transition-colors uppercase tracking-wider"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Auto mode waiting indicator */}
          {maneuverMode === 'auto' && isCritical && (
            <div className="flex items-center gap-2 text-[10px] text-green-400 font-bold animate-pulse">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
              AUTO-EXECUTING IN 1.5s...
            </div>
          )}
        </div>
      )}

      {/* Nominal state */}
      {!isSimulating && !urgentAlert && (
        <div className="px-4 py-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-green-500/10 flex items-center justify-center">
            <span className="text-green-500 text-lg">✓</span>
          </div>
          <div>
            <p className="text-sm text-blue-400 font-medium">System Nominal</p>
            <p className="text-[10px] text-gray-500">No maneuver required</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default ManeuverPanel
