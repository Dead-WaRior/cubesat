import { useState } from 'react'
import useDashboardStore from '../store'

/**
 * Derive delta-V recommendations from the most severe active alert.
 * @param {import('../store').Alert} alert
 * @returns {string[]}
 */
function buildRecommendations(alert) {
  if (!alert) return []

  const recs = []
  if (alert.recommended_action) recs.push(alert.recommended_action)

  if (alert.alert_level === 'critical') {
    recs.push('Execute emergency avoidance burn immediately')
    recs.push('Estimated Δv: 0.5 – 2.0 m/s along velocity vector')
  } else if (alert.alert_level === 'warning') {
    recs.push('Schedule precautionary avoidance maneuver')
    recs.push('Estimated Δv: 0.1 – 0.5 m/s along velocity vector')
  }

  return [...new Set(recs)] // deduplicate
}

/**
 * ManeuverPanel
 *
 * Displays maneuver recommendations when WARNING or CRITICAL alerts are
 * active.  The operator can approve or dismiss the recommendation.
 * Shows a nominal status message when no action is required.
 */
function ManeuverPanel() {
  const alerts = useDashboardStore((s) => s.alerts)
  const acknowledgeAlert = useDashboardStore((s) => s.acknowledgeAlert)

  const [dismissed, setDismissed] = useState(false)

  // Find the most severe unacknowledged actionable alert
  const urgentAlert = alerts
    .filter(
      (a) =>
        !a.acknowledged &&
        (a.alert_level === 'warning' || a.alert_level === 'critical'),
    )
    .sort((a, b) => {
      const rank = { critical: 2, warning: 1 }
      return (rank[b.alert_level] ?? 0) - (rank[a.alert_level] ?? 0)
    })[0]

  const recommendations = buildRecommendations(urgentAlert)
  const isCritical = urgentAlert?.alert_level === 'critical'

  if (!urgentAlert || dismissed) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-700 px-4 py-4">
        <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase mb-2">
          Maneuver Recommendation
        </h2>
        <div className="flex items-center gap-2 text-green-400 text-sm">
          <span className="text-green-500 text-lg">✓</span>
          No maneuver required — system nominal
        </div>
      </div>
    )
  }

  return (
    <div
      className={`rounded-xl border overflow-hidden ${
        isCritical
          ? 'bg-red-950/30 border-red-600'
          : 'bg-orange-950/30 border-orange-600'
      }`}
    >
      {/* Header */}
      <div
        className={`px-4 py-3 border-b flex items-center justify-between ${
          isCritical ? 'border-red-700' : 'border-orange-700'
        }`}
      >
        <h2 className="text-sm font-semibold tracking-wide uppercase text-gray-200">
          {isCritical ? '🚨 ' : '⚠ '}Maneuver Recommendation
        </h2>
        <span
          className={`text-xs font-bold uppercase px-2 py-0.5 rounded ${
            isCritical ? 'bg-red-600 text-white' : 'bg-orange-500 text-white'
          }`}
        >
          {urgentAlert.alert_level}
        </span>
      </div>

      {/* Details */}
      <div className="px-4 py-3 space-y-1.5 text-xs text-gray-300">
        <div>
          <span className="text-gray-500">Track:</span>{' '}
          <span className="font-mono">{urgentAlert.track_id}</span>
        </div>
        {typeof urgentAlert.tca_min === 'number' && (
          <div>
            <span className="text-gray-500">TCA:</span>{' '}
            <span className="font-mono">{urgentAlert.tca_min.toFixed(1)} min</span>
          </div>
        )}
        {typeof urgentAlert.pc === 'number' && (
          <div>
            <span className="text-gray-500">Pc:</span>{' '}
            <span className="font-mono">{urgentAlert.pc.toExponential(2)}</span>
          </div>
        )}
      </div>

      {/* Recommendations list */}
      {recommendations.length > 0 && (
        <ul className="px-4 pb-3 space-y-1.5 text-xs">
          {recommendations.map((rec, i) => (
            <li key={i} className="flex gap-2 text-gray-300">
              <span className={isCritical ? 'text-red-400' : 'text-orange-400'}>→</span>
              {rec}
            </li>
          ))}
        </ul>
      )}

      {/* Action buttons */}
      <div className="px-4 py-3 border-t border-gray-700 flex gap-2">
        <button
          onClick={() => acknowledgeAlert(urgentAlert.alert_id)}
          className="flex-1 bg-green-600 hover:bg-green-500 active:bg-green-700 text-white text-xs font-semibold py-1.5 px-3 rounded transition-colors"
        >
          Approve Maneuver
        </button>
        <button
          onClick={() => setDismissed(true)}
          className="flex-1 bg-gray-700 hover:bg-gray-600 active:bg-gray-800 text-gray-200 text-xs font-semibold py-1.5 px-3 rounded transition-colors"
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}

export default ManeuverPanel
