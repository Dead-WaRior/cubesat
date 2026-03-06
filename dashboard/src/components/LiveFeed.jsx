import useDashboardStore from '../store'

/**
 * Returns Tailwind border-color class based on detection confidence.
 * @param {number} confidence
 * @returns {string}
 */
function confidenceColor(confidence) {
  if (confidence > 0.7) return 'border-green-500'
  if (confidence >= 0.4) return 'border-yellow-400'
  return 'border-red-500'
}

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
            className={`inline-block w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
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
            {/* Bounding box overlays */}
            {tracks.map((track) => {
              if (!track.bbox) return null
              const { x, y, w, h } = track.bbox
              return (
                <div
                  key={track.track_id}
                  className={`absolute border-2 ${confidenceColor(track.confidence)}`}
                  style={{
                    left: `${x}px`,
                    top: `${y}px`,
                    width: `${w}px`,
                    height: `${h}px`,
                  }}
                >
                  {/* Track ID label */}
                  <span
                    className={`absolute -top-5 left-0 text-[10px] font-mono px-1 rounded-sm bg-black/60 ${
                      track.confidence > 0.7
                        ? 'text-green-400'
                        : track.confidence >= 0.4
                        ? 'text-yellow-300'
                        : 'text-red-400'
                    }`}
                  >
                    {track.track_id}
                  </span>
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
