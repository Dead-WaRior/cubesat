import PropTypes from 'prop-types'
import useDashboardStore from '../store'

/**
 * Returns Tailwind row background classes for a given alert level.
 * @param {string|undefined} alertLevel
 * @returns {string}
 */
function rowBg(alertLevel) {
  switch (alertLevel) {
    case 'critical':
      return 'bg-red-950/60 hover:bg-red-950/80'
    case 'warning':
      return 'bg-orange-950/50 hover:bg-orange-950/70'
    case 'advisory':
      return 'bg-yellow-950/40 hover:bg-yellow-950/60'
    default:
      return 'hover:bg-gray-800/50'
  }
}

/**
 * Returns a badge element for a given alert level.
 * @param {{ alertLevel: string }} props
 */
function AlertBadge({ alertLevel }) {
  AlertBadge.propTypes = { alertLevel: PropTypes.string }
  const base = 'inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider'
  switch (alertLevel) {
    case 'critical':
      return <span className={`${base} bg-red-600 text-white`}>Critical</span>
    case 'warning':
      return <span className={`${base} bg-orange-500 text-white`}>Warning</span>
    case 'advisory':
      return <span className={`${base} bg-yellow-500 text-gray-900`}>Advisory</span>
    default:
      return <span className={`${base} bg-gray-600 text-gray-200`}>—</span>
  }
}

/**
 * Format a Pc value as scientific notation (e.g. 1.23e-4).
 * @param {number|undefined} pc
 * @returns {string}
 */
function formatPc(pc) {
  if (pc == null || isNaN(pc)) return '—'
  return pc.toExponential(2)
}

/**
 * TracksTable
 *
 * Displays a sortable table of all currently active debris tracks with
 * colour-coded rows indicating their alert severity.
 */
function TracksTable() {
  const tracks = useDashboardStore((s) => s.tracks)

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700">
        <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">
          Active Debris Tracks
          <span className="ml-2 text-xs font-normal text-gray-400">
            ({tracks.length} object{tracks.length !== 1 ? 's' : ''})
          </span>
        </h2>
      </div>

      <div className="overflow-x-auto">
        {tracks.length === 0 ? (
          <div className="flex items-center justify-center py-10 text-gray-500 text-sm">
            No active debris tracks detected
          </div>
        ) : (
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="border-b border-gray-700 bg-gray-800/60 text-gray-400 uppercase tracking-wider">
                <th className="px-3 py-2">Track ID</th>
                <th className="px-3 py-2">Position (x, y)</th>
                <th className="px-3 py-2">Velocity (m/s)</th>
                <th className="px-3 py-2">Pc</th>
                <th className="px-3 py-2">Alert</th>
                <th className="px-3 py-2">TCA (min)</th>
                <th className="px-3 py-2">Age (fr)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {tracks.map((track) => (
                <tr key={track.track_id} className={`transition-colors ${rowBg(track.alert_level)}`}>
                  <td className="px-3 py-2 font-mono text-gray-300">{track.track_id}</td>
                  <td className="px-3 py-2 font-mono text-gray-300">
                    ({typeof track.x === 'number' ? track.x.toFixed(3) : '—'},&nbsp;
                    {typeof track.y === 'number' ? track.y.toFixed(3) : '—'})
                  </td>
                  <td className="px-3 py-2 font-mono text-gray-300">
                    {typeof track.vx === 'number' && typeof track.vy === 'number'
                      ? Math.hypot(track.vx, track.vy).toFixed(1)
                      : '—'}
                  </td>
                  <td className="px-3 py-2 font-mono text-gray-200">{formatPc(track.pc)}</td>
                  <td className="px-3 py-2">
                    <AlertBadge alertLevel={track.alert_level} />
                  </td>
                  <td className="px-3 py-2 font-mono text-gray-300">
                    {typeof track.tca_min === 'number' ? track.tca_min.toFixed(1) : '—'}
                  </td>
                  <td className="px-3 py-2 font-mono text-gray-400">
                    {track.age_frames ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default TracksTable
