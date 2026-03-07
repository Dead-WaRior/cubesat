import useDashboardStore from '../store'


/**
 * LiveFeed
 *
 * Displays the latest camera frame from the satellite with bounding-box
 * overlays for each active debris track.  When no frame is available a
 * dark placeholder is shown instead.
 */
function LiveFeed() {
  const frame = useDashboardStore((s) => s.frame)
  const tracks = useDashboardStore((s) => s.tracks)
  const isConnected = useDashboardStore((s) => s.isConnected)

  return (
    <div className="glass-card rounded-xl overflow-hidden shadow-lg">
      {/* Header */}
      <div className="glass-header">
        <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">
          Live Camera Feed
        </h2>
        <span className="flex items-center gap-1.5 text-xs">
          <span
            className={`inline-block w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}
          />
          <span className={isConnected ? 'text-green-400' : 'text-red-400'}>
            {isConnected ? 'LIVE' : 'DISCONNECTED'}
          </span>
        </span>
      </div>

      {/* Feed area */}
      <div className="relative w-full" style={{ aspectRatio: '16/9' }}>
        {frame ? (
          <>
            <img
              src={frame}
              alt="Live satellite feed"
              className="absolute inset-0 w-full h-full object-cover"
            />
            {tracks.map((track) => {
              if (!track.bbox) return null
              const { x, y, w, h } = track.bbox
              const isHighRisk = track.alert_level === 'critical' || track.alert_level === 'warning'
              const isCritical = track.alert_level === 'critical'
              const colorClass = isCritical ? 'border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.8)]' : isHighRisk ? 'border-orange-500' : 'border-green-500'

              const velocityKmS = typeof track.vx === 'number' && typeof track.vy === 'number'
                ? (Math.hypot(track.vx, track.vy)).toFixed(1)
                : '—'
              const distMeters = typeof track.tca_min === 'number' && typeof track.vx === 'number'
                ? (Math.max(0, track.tca_min * 60 * Math.hypot(track.vx, track.vy)) / 1000).toFixed(0)
                : '—'

              return (
                <div
                  key={track.track_id}
                  className={`absolute border-2 ${colorClass} transition-all duration-300`}
                  style={{
                    left: `${x}px`,
                    top: `${y}px`,
                    width: `${w}px`,
                    height: `${h}px`,
                  }}
                >
                  {/* Track ID label */}
                  <div
                    className={`absolute -top-[4rem] left-0 text-[9px] font-mono px-1.5 py-1 rounded-sm bg-black/80 whitespace-nowrap ${isCritical ? 'text-red-400 border border-red-500/50' : isHighRisk ? 'text-orange-400' : 'text-green-400'
                      }`}
                  >
                    <div className="font-bold border-b border-white/10 pb-0.5 mb-0.5">Debris ID-{String(track.track_id).padStart(3, '0')}</div>
                    <div>Distance: {distMeters !== '—' ? `${distMeters} m` : '—'}</div>
                    <div>Rel Speed: {velocityKmS !== '—' ? `${velocityKmS} km/s` : '—'}</div>
                  </div>

                  {isCritical && (
                    <div className="absolute inset-x-0 -bottom-5 flex justify-center">
                      <span className="bg-red-600 text-white text-[8px] px-1 font-bold animate-pulse">LOCK</span>
                    </div>
                  )}
                </div>
              )
            })}
          </>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-950 gap-3">
            <svg
              className="w-12 h-12 text-gray-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 10l4.553-2.069A1 1 0 0121 8.82V15.18a1 1 0 01-1.447.89L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"
              />
            </svg>
            <p className="text-gray-500 text-sm">Awaiting satellite feed...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default LiveFeed
