import { useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import useDashboardStore from '../store'

/** Palette for up to 8 simultaneous tracks */
const TRACK_COLORS = [
  '#60a5fa', // blue-400
  '#34d399', // emerald-400
  '#f472b6', // pink-400
  '#fb923c', // orange-400
  '#a78bfa', // violet-400
  '#facc15', // yellow-400
  '#2dd4bf', // teal-400
  '#f87171', // red-400
]

/**
 * Convert a Unix timestamp to "seconds ago" relative to now.
 * @param {number} ts - Unix epoch seconds
 * @returns {number}
 */
function secsAgo(ts) {
  return Math.round(Date.now() / 1000 - ts)
}

/**
 * RiskTimeline
 *
 * Renders a Recharts line chart showing the Probability of Collision (Pc)
 * for each active track over the past 30 seconds of recorded history.
 * Each track is drawn in a unique colour and identified in the legend.
 */
function RiskTimeline() {
  const pcHistory = useDashboardStore((s) => s.pcHistory)
  const tracks = useDashboardStore((s) => s.tracks)

  // Build a unified time-series dataset keyed by "seconds ago"
  const { chartData, trackIds } = useMemo(() => {
    const activeIds = tracks.map((t) => t.track_id)

    // Collect all unique timestamps across active tracks
    const tsSet = new Set()
    activeIds.forEach((id) => {
      pcHistory[id] != null && pcHistory[id].forEach((pt) => tsSet.add(pt.timestamp))
    })

    const sortedTs = [...tsSet].sort((a, b) => a - b)

    // Build per-timestamp rows
    const rows = sortedTs.map((ts) => {
      const row = { secsAgo: secsAgo(ts) }
      activeIds.forEach((id) => {
        const match = (pcHistory[id] ?? []).find((p) => p.timestamp === ts)
        if (match) row[id] = match.pc
      })
      return row
    })

    return { chartData: rows, trackIds: activeIds }
  }, [pcHistory, tracks])

  const isEmpty = chartData.length === 0

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700">
        <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">
          Probability of Collision Timeline
        </h2>
        <p className="text-xs text-gray-500 mt-0.5">Last 30 seconds per track</p>
      </div>

      <div className="px-2 py-4" style={{ height: 220 }}>
        {isEmpty ? (
          <div className="flex items-center justify-center h-full text-gray-500 text-sm">
            No Pc history recorded yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 4, right: 12, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="secsAgo"
                reversed
                tickFormatter={(v) => `${v}s`}
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                label={{
                  value: 'seconds ago',
                  position: 'insideBottom',
                  offset: -2,
                  fill: '#6b7280',
                  fontSize: 10,
                }}
              />
              <YAxis
                tickFormatter={(v) => v.toExponential(1)}
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: 6,
                  fontSize: 11,
                }}
                labelFormatter={(v) => `${v}s ago`}
                formatter={(value, name) => [value.toExponential(3), name]}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, paddingTop: 8, color: '#d1d5db' }}
              />
              {trackIds.map((id, i) => (
                <Line
                  key={id}
                  type="monotone"
                  dataKey={id}
                  stroke={TRACK_COLORS[i % TRACK_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

export default RiskTimeline
