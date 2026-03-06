import PropTypes from 'prop-types'
import useDashboardStore from '../store'

/**
 * @typedef {'ok'|'degraded'|'error'|'unknown'|'connected'|'disconnected'} HealthStatus
 */

/**
 * Returns Tailwind dot-color class for a health status.
 * @param {HealthStatus} status
 * @returns {string}
 */
function dotColor(status) {
  switch (status) {
    case 'ok':
    case 'connected':
      return 'bg-green-500'
    case 'degraded':
      return 'bg-yellow-400'
    case 'error':
    case 'disconnected':
      return 'bg-red-500'
    default:
      return 'bg-gray-500'
  }
}

/**
 * Returns a human-readable label for a health status.
 * @param {HealthStatus} status
 * @returns {string}
 */
function statusLabel(status) {
  switch (status) {
    case 'ok':
      return 'OK'
    case 'connected':
      return 'Connected'
    case 'degraded':
      return 'Degraded'
    case 'error':
      return 'Error'
    case 'disconnected':
      return 'Disconnected'
    default:
      return 'Unknown'
  }
}

/**
 * Returns Tailwind text-color class for a health status.
 * @param {HealthStatus} status
 * @returns {string}
 */
function textColor(status) {
  switch (status) {
    case 'ok':
    case 'connected':
      return 'text-green-400'
    case 'degraded':
      return 'text-yellow-400'
    case 'error':
    case 'disconnected':
      return 'text-red-400'
    default:
      return 'text-gray-500'
  }
}

/**
 * Single status row.
 * @param {{ label: string, status: HealthStatus }} props
 */
function StatusRow({ label, status }) {
  StatusRow.propTypes = { label: PropTypes.string, status: PropTypes.string }
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-gray-800 last:border-0">
      <span className="text-xs text-gray-400">{label}</span>
      <div className="flex items-center gap-1.5">
        <span className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${dotColor(status)}`} />
        <span className={`text-xs font-medium ${textColor(status)}`}>{statusLabel(status)}</span>
      </div>
    </div>
  )
}

/**
 * SystemHealth
 *
 * Displays the operational status of each subsystem layer: Simulation,
 * Ingestion, Vision, Prediction, and the Dashboard WebSocket connection.
 */
function SystemHealth() {
  const health = useDashboardStore((s) => s.systemHealth)
  const isConnected = useDashboardStore((s) => s.isConnected)

  const layers = [
    { label: 'Simulation', status: health.simulation },
    { label: 'Ingestion', status: health.ingestion },
    { label: 'Vision', status: health.vision },
    { label: 'Prediction', status: health.prediction },
    { label: 'Dashboard', status: isConnected ? 'connected' : 'disconnected' },
  ]

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700">
        <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">
          System Health
        </h2>
      </div>
      <div className="px-4 py-1">
        {layers.map(({ label, status }) => (
          <StatusRow key={label} label={label} status={status} />
        ))}
      </div>
    </div>
  )
}

export default SystemHealth
