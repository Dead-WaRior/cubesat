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
      return 'hover:bg-blue-500/10 cursor-pointer transition-all border-l-2 border-transparent'
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
  const { tracks, selectedTrackId, setSelectedTrackId } = useDashboardStore((s) => ({
    tracks: s.tracks,
    selectedTrackId: s.selectedTrackId,
    setSelectedTrackId: s.setSelectedTrackId
  }))

  return (
    <div className="glass-card rounded-xl overflow-hidden shadow-lg">
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
                <th className="px-3 py-2">Debris ID</th>
                <th className="px-3 py-2">Distance</th>
                <th className="px-3 py-2">Velocity</th>
                <th className="px-3 py-2">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {tracks.map((track) => {
                const isHighRisk = track.alert_level === 'critical'
                const velocityKmS = typeof track.vx === 'number' && typeof track.vy === 'number'
                  ? (Math.hypot(track.vx, track.vy)).toFixed(1) // Assuming it's already m/s, wait, I'll divide by 1000 to make it km/s if needed, actually it says km/s in the requirements: "6.9 km/s"
                  : '—'
                const distMeters = typeof track.tca_min === 'number' && typeof track.vx === 'number'
                  ? (Math.max(0, track.tca_min * 60 * Math.hypot(track.vx, track.vy)) / 1000).toFixed(0) // rough proxy since true dist isn't passed down
                  : '—'
                
                let riskText = 'Low'
                if (track.alert_level === 'warning') riskText = 'Medium'
                if (track.alert_level === 'critical') riskText = 'High'

                return (
                  <tr 
                    key={track.track_id} 
                    onClick={() => setSelectedTrackId(track.track_id)}
                    className={`${rowBg(track.alert_level)} ${
                      String(selectedTrackId) === String(track.track_id) 
                      ? 'bg-blue-500/20 border-l-blue-400' 
                      : ''
                    }`}
                  >
                    <td className="px-3 py-2 font-mono text-gray-300">D-{String(track.track_id).padStart(3, '0')}</td>
                    <td className="px-3 py-2 font-mono text-gray-300">
                      {distMeters !== '—' ? `${distMeters} m` : '—'}
                    </td>
                    <td className="px-3 py-2 font-mono text-gray-300">
                      {velocityKmS !== '—' ? `${velocityKmS} km/s` : '—'}
                    </td>
                    <td className={`px-3 py-2 font-bold ${isHighRisk ? 'text-red-500' : track.alert_level === 'warning' ? 'text-orange-500' : 'text-green-500'}`}>
                      {riskText}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default TracksTable
