import PropTypes from 'prop-types'
import useDashboardStore from '../store'

/**
 * CriticalModal
 *
 * Full-screen blocking overlay that appears whenever there is at least one
 * unacknowledged CRITICAL alert.  The operator must explicitly click
 * "ACKNOWLEDGE & DISMISS" — clicking outside the modal has no effect.
 *
 * Renders nothing when no critical unacknowledged alerts exist.
 */
function CriticalModal() {
  const alerts = useDashboardStore((s) => s.alerts)
  const acknowledgeAlert = useDashboardStore((s) => s.acknowledgeAlert)

  // Find the most recent unacknowledged critical alert
  const criticalAlert = [...alerts]
    .reverse()
    .find((a) => a.alert_level === 'critical' && !a.acknowledged)

  if (!criticalAlert) return null

  return (
    /* Overlay — pointer-events on the backdrop are disabled to prevent
       accidental dismissal by clicking outside the modal card. */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      aria-modal="true"
      role="alertdialog"
      aria-labelledby="critical-modal-title"
    >
      <div
        className="relative w-full max-w-lg mx-4 bg-gray-950 border-2 border-red-600 rounded-2xl shadow-2xl shadow-red-900/50 animate-pulse-border"
        style={{ animation: 'pulseBorder 1.5s ease-in-out infinite' }}
        /* Stop propagation so clicking inside the card never reaches the
           backdrop (belt-and-suspenders since backdrop has no onClick). */
        onClick={(e) => e.stopPropagation()}
      >
        {/* Pulse ring */}
        <style>{`
          @keyframes pulseBorder {
            0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.6), 0 25px 60px -15px rgba(127,29,29,0.5); }
            50%       { box-shadow: 0 0 0 8px rgba(239,68,68,0),  0 25px 60px -15px rgba(127,29,29,0.5); }
          }
        `}</style>

        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-red-800">
          <span className="text-3xl select-none" role="img" aria-label="warning">🚨</span>
          <div>
            <h2
              id="critical-modal-title"
              className="text-lg font-bold text-red-400 uppercase tracking-wide"
            >
              Critical Collision Alert
            </h2>
            <p className="text-xs text-red-300/70">Immediate action required</p>
          </div>
        </div>

        {/* Alert details */}
        <div className="px-6 py-5 space-y-3 text-sm">
          <DetailRow label="Track ID" value={criticalAlert.track_id} mono />
          <DetailRow
            label="Probability of Collision (Pc)"
            value={
              typeof criticalAlert.pc === 'number'
                ? criticalAlert.pc.toExponential(3)
                : '—'
            }
            mono
            highlight
          />
          <DetailRow
            label="Time to Closest Approach"
            value={
              typeof criticalAlert.tca_min === 'number'
                ? `${criticalAlert.tca_min.toFixed(1)} minutes`
                : '—'
            }
            mono
          />
          <DetailRow
            label="Miss Distance"
            value={
              typeof criticalAlert.miss_distance_km === 'number'
                ? `${criticalAlert.miss_distance_km.toFixed(3)} km`
                : '—'
            }
            mono
          />
          {criticalAlert.recommended_action && (
            <div className="mt-3 rounded-lg bg-red-950/50 border border-red-800 px-4 py-3">
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
                Recommended Action
              </p>
              <p className="text-red-200 font-medium">{criticalAlert.recommended_action}</p>
            </div>
          )}
        </div>

        {/* Timestamp */}
        {criticalAlert.timestamp && (
          <p className="px-6 pb-1 text-xs text-gray-600">
            Alert received: {new Date(criticalAlert.timestamp).toLocaleString()}
          </p>
        )}

        {/* Action button */}
        <div className="px-6 py-4 border-t border-red-900">
          <button
            onClick={() => acknowledgeAlert(criticalAlert.alert_id)}
            className="w-full bg-red-600 hover:bg-red-500 active:bg-red-700 text-white font-bold py-3 px-6 rounded-lg text-sm uppercase tracking-widest transition-colors focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2 focus:ring-offset-gray-950"
            autoFocus
          >
            Acknowledge &amp; Dismiss
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * A single key-value row within the modal detail section.
 * @param {{ label: string, value: string, mono?: boolean, highlight?: boolean }} props
 */
function DetailRow({ label, value, mono = false, highlight = false }) {
  DetailRow.propTypes = {
    label: PropTypes.string,
    value: PropTypes.string,
    mono: PropTypes.bool,
    highlight: PropTypes.bool,
  }
  return (
    <div className="flex justify-between items-baseline gap-4">
      <span className="text-gray-500 flex-shrink-0">{label}</span>
      <span
        className={`text-right ${mono ? 'font-mono' : ''} ${
          highlight ? 'text-red-300 font-semibold text-base' : 'text-gray-200'
        }`}
      >
        {value}
      </span>
    </div>
  )
}

export default CriticalModal
