import PropTypes from 'prop-types'
import useDashboardStore from '../store'

/**
 * Returns left-border and background styling classes for an alert row.
 * @param {string} level - 'advisory' | 'warning' | 'critical'
 * @returns {string}
 */
function alertRowStyle(level) {
  switch (level) {
    case 'critical':
      return 'border-l-4 border-red-500 bg-red-950/40'
    case 'warning':
      return 'border-l-4 border-orange-500 bg-orange-950/30'
    case 'advisory':
      return 'border-l-4 border-yellow-500'
    default:
      return 'border-l-4 border-gray-700'
  }
}

/**
 * Badge for alert level label.
 * @param {{ level: string }} props
 */
function LevelBadge({ level }) {
  LevelBadge.propTypes = { level: PropTypes.string }
  const base = 'text-[10px] font-bold uppercase px-1.5 py-0.5 rounded tracking-wider'
  switch (level) {
    case 'critical':
      return <span className={`${base} bg-red-600 text-white`}>Critical</span>
    case 'warning':
      return <span className={`${base} bg-orange-500 text-white`}>⚠ Warning</span>
    case 'advisory':
      return <span className={`${base} bg-yellow-500 text-gray-900`}>Advisory</span>
    default:
      return <span className={`${base} bg-gray-600 text-gray-200`}>{level}</span>
  }
}

/**
 * Format an ISO timestamp to a short locale time string.
 * @param {string} ts
 * @returns {string}
 */
function formatTime(ts) {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleTimeString()
  } catch {
    return ts
  }
}

/**
 * AlertFeed
 *
 * Scrollable feed showing the most recent 50 alerts, newest at the top.
 * Each entry is colour-coded by severity level and displays key orbital
 * conjunction metrics alongside the recommended action.
 */
function AlertFeed() {
  const alerts = useDashboardStore((s) => s.alerts)

  // Show newest first
  const sorted = [...alerts].reverse()

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden flex flex-col">
      <div className="px-4 py-3 border-b border-gray-700 flex-shrink-0">
        <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">
          Alert Feed
          <span className="ml-2 text-xs font-normal text-gray-400">
            ({alerts.length} / 50)
          </span>
        </h2>
      </div>

      <div className="overflow-y-auto scrollbar-thin" style={{ maxHeight: 340 }}>
        {sorted.length === 0 ? (
          <div className="flex items-center justify-center py-10 text-gray-500 text-sm">
            No alerts recorded
          </div>
        ) : (
          <ul className="divide-y divide-gray-800">
            {sorted.map((alert) => (
              <li
                key={alert.alert_id ?? `${alert.track_id}-${alert.timestamp}`}
                className={`px-3 py-2.5 text-xs ${alertRowStyle(alert.alert_level)} ${
                  alert.acknowledged ? 'opacity-50' : ''
                }`}
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    <LevelBadge level={alert.alert_level} />
                    <span className="font-mono text-gray-300">{alert.track_id}</span>
                  </div>
                  <span className="text-gray-500">{formatTime(alert.timestamp)}</span>
                </div>

                <div className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-0.5 text-gray-400">
                  <span>
                    Pc:{' '}
                    <span className="text-gray-200 font-mono">
                      {typeof alert.pc === 'number' ? alert.pc.toExponential(2) : '—'}
                    </span>
                  </span>
                  <span>
                    Miss:{' '}
                    <span className="text-gray-200 font-mono">
                      {typeof alert.miss_distance_km === 'number'
                        ? `${alert.miss_distance_km.toFixed(2)} km`
                        : '—'}
                    </span>
                  </span>
                  <span>
                    TCA:{' '}
                    <span className="text-gray-200 font-mono">
                      {typeof alert.tca_min === 'number'
                        ? `${alert.tca_min.toFixed(1)} min`
                        : '—'}
                    </span>
                  </span>
                </div>

                {alert.recommended_action && (
                  <p className="mt-1 text-gray-400 italic leading-snug">
                    → {alert.recommended_action}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default AlertFeed
