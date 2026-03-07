import { useState, useCallback } from 'react'
import useDashboardStore from '../store'

/**
 * CriticalModal → Side Notification Panel
 *
 * Slides in from the top-right as a non-blocking notification toast.
 * Visually prominent but doesn't obstruct the orbital simulation area.
 * Auto-dismisses after 15 seconds or on manual click.
 */
const COOLDOWN_MS = 30000

function CriticalModal() {
  const alerts = useDashboardStore((s) => s.alerts)
  const acknowledgeAlert = useDashboardStore((s) => s.acknowledgeAlert)
  const [suppressedUntil, setSuppressedUntil] = useState(0)

  const criticalAlert = [...alerts]
    .reverse()
    .find((a) => a.alert_level === 'critical' && !a.acknowledged)

  const handleDismiss = useCallback(() => {
    if (criticalAlert) {
      alerts.forEach((a) => {
        if (a.alert_level === 'critical' && !a.acknowledged) {
          acknowledgeAlert(a.alert_id)
        }
      })
      setSuppressedUntil(Date.now() + COOLDOWN_MS)
    }
  }, [criticalAlert, alerts, acknowledgeAlert])

  if (!criticalAlert || Date.now() < suppressedUntil) return null

  return (
    <>
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(120%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes criticalPulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.5), 0 8px 32px rgba(0,0,0,0.4); }
          50% { box-shadow: 0 0 0 6px rgba(239,68,68,0), 0 8px 32px rgba(0,0,0,0.4); }
        }
        @keyframes redGlow {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.8; }
        }
      `}</style>

      <div
        className="fixed top-24 right-4 z-50 w-[360px] max-w-[calc(100vw-2rem)]"
        style={{ animation: 'slideInRight 0.4s cubic-bezier(0.16,1,0.3,1) forwards' }}
      >
        <div
          className="bg-gray-950/95 backdrop-blur-xl border border-red-600 rounded-xl overflow-hidden"
          style={{ animation: 'criticalPulse 2s ease-in-out infinite' }}
        >
          {/* Red accent strip */}
          <div className="h-1 bg-gradient-to-r from-red-600 via-red-400 to-red-600"
            style={{ animation: 'redGlow 1.5s ease-in-out infinite' }} />

          {/* Header */}
          <div className="flex items-center gap-2.5 px-4 py-3 border-b border-red-900/50">
            <div className="w-8 h-8 rounded-full bg-red-600/20 flex items-center justify-center flex-shrink-0">
              <span className="text-lg" role="img" aria-label="alert">🚨</span>
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-sm font-bold text-red-400 uppercase tracking-wide">
                Collision Alert
              </h2>
              <p className="text-[10px] text-red-300/60">Immediate action required</p>
            </div>
            <button
              onClick={handleDismiss}
              className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-gray-500 hover:text-white transition-colors flex-shrink-0"
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>

          {/* Alert details */}
          <div className="px-4 py-3 space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-black/30 rounded-lg px-3 py-2">
                <span className="text-[9px] text-gray-500 uppercase block">Track ID</span>
                <span className="font-mono text-white text-sm">{criticalAlert.track_id}</span>
              </div>
              <div className="bg-black/30 rounded-lg px-3 py-2">
                <span className="text-[9px] text-gray-500 uppercase block">Collision Prob</span>
                <span className="font-mono text-red-400 text-sm font-bold">
                  {typeof criticalAlert.pc === 'number' ? criticalAlert.pc.toExponential(2) : '—'}
                </span>
              </div>
              <div className="bg-black/30 rounded-lg px-3 py-2">
                <span className="text-[9px] text-gray-500 uppercase block">TCA</span>
                <span className="font-mono text-white text-sm">
                  {typeof criticalAlert.tca_min === 'number' ? `${criticalAlert.tca_min.toFixed(1)} min` : '—'}
                </span>
              </div>
              <div className="bg-black/30 rounded-lg px-3 py-2">
                <span className="text-[9px] text-gray-500 uppercase block">Miss Dist</span>
                <span className="font-mono text-white text-sm">
                  {typeof criticalAlert.miss_distance_km === 'number' ? `${criticalAlert.miss_distance_km.toFixed(2)} km` : '—'}
                </span>
              </div>
            </div>

            {criticalAlert.recommended_action && (
              <div className="rounded-lg bg-red-950/40 border border-red-800/50 px-3 py-2">
                <p className="text-[9px] text-gray-400 uppercase mb-0.5">Action</p>
                <p className="text-red-200 text-xs font-medium">{criticalAlert.recommended_action}</p>
              </div>
            )}
          </div>

          {/* Action button */}
          <div className="px-4 pb-3">
            <button
              onClick={handleDismiss}
              className="w-full bg-red-600/80 hover:bg-red-500 text-white font-bold py-2 px-4 rounded-lg text-xs uppercase tracking-widest transition-all hover:shadow-[0_0_20px_rgba(239,68,68,0.3)]"
            >
              Acknowledge
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

export default CriticalModal
