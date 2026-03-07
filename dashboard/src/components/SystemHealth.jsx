import PropTypes from 'prop-types'
import useDashboardStore from '../store'

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

function statusLabel(status) {
  switch (status) {
    case 'ok': return 'OK'
    case 'connected': return 'Connected'
    case 'degraded': return 'Degraded'
    case 'error': return 'Error'
    case 'disconnected': return 'Disconnected'
    default: return 'Unknown'
  }
}

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
 * Fixed: uses reactive Zustand selectors for real-time telemetry updates
 * instead of static getState() calls.
 */
function SystemHealth() {
  const health = useDashboardStore((s) => s.systemHealth)
  const isConnected = useDashboardStore((s) => s.isConnected)
  const satBusStats = useDashboardStore((s) => s.satBusStats)
  const satLla = useDashboardStore((s) => s.satLla)

  const layers = [
    { label: 'Simulation Engine', status: health.simulation },
    { label: 'Vision Detection Engine', status: health.vision },
    { label: 'Trajectory Prediction Engine', status: health.prediction },
    { label: 'Collision Risk Analyzer', status: health.prediction },
    { label: 'Alert System', status: health.ingestion },
  ]

  const batteryPct = Math.round((satBusStats.battery_v / 14) * 100)
  const cpuTemp = satBusStats.cpu_temp ?? 42.0
  const cpuLoad = satBusStats.load_pct ?? 25.0
  const altitude = satLla?.alt ?? 400.0
  const isCpuHot = cpuTemp > 50

  return (
    <div className="glass-card rounded-xl overflow-hidden shadow-lg">
      <div className="glass-header">
        <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">
          System Health
        </h2>
      </div>
      <div className="px-4 py-1">
        {layers.map(({ label, status }) => (
          <StatusRow key={label} label={label} status={status} />
        ))}
      </div>

      <div className="glass-header border-t border-white/5 mt-2 flex justify-between">
        <h2 className="text-[10px] font-black text-gray-500 tracking-wider uppercase">
          Satellite Telemetry
        </h2>
        <span className={`text-[8px] font-mono px-1.5 rounded ${isCpuHot ? 'text-orange-400 bg-orange-500/20' : 'text-green-400 bg-green-500/20'
          }`}>
          {isCpuHot ? 'ELEVATED' : 'NOMINAL'}
        </span>
      </div>

      <div className="px-4 py-3 space-y-3">
        {/* Battery Bar */}
        <div className="flex justify-between items-end">
          <span className="text-[10px] text-gray-400 uppercase font-bold">Battery Level</span>
          <div className="flex gap-2 items-center w-3/5">
            <div className="flex-1 bg-black/40 h-2 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-700 ${batteryPct > 50 ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' :
                    batteryPct > 20 ? 'bg-yellow-500 shadow-[0_0_8px_#eab308]' :
                      'bg-red-500 shadow-[0_0_8px_#ef4444]'
                  }`}
                style={{ width: `${Math.min(100, batteryPct)}%` }}
              />
            </div>
            <span className="text-xs font-mono text-green-400 w-8 text-right">{batteryPct}%</span>
          </div>
        </div>

        {/* CPU & Temperature Row */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-black/20 rounded-lg px-3 py-2 border border-white/5">
            <span className="text-[9px] text-gray-500 uppercase font-bold block mb-1">CPU Temp</span>
            <div className="flex items-baseline gap-1">
              <span className={`text-lg font-mono font-bold transition-colors ${cpuTemp > 60 ? 'text-red-400' :
                  cpuTemp > 50 ? 'text-orange-400' :
                    'text-green-400'
                }`}>
                {cpuTemp.toFixed(1)}
              </span>
              <span className="text-[10px] text-gray-500">°C</span>
            </div>
            {/* Mini temp bar */}
            <div className="w-full bg-black/40 h-1 rounded-full mt-1.5 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${cpuTemp > 60 ? 'bg-red-500' :
                    cpuTemp > 50 ? 'bg-orange-500' :
                      'bg-green-500'
                  }`}
                style={{ width: `${Math.min(100, (cpuTemp / 80) * 100)}%` }}
              />
            </div>
          </div>

          <div className="bg-black/20 rounded-lg px-3 py-2 border border-white/5">
            <span className="text-[9px] text-gray-500 uppercase font-bold block mb-1">CPU Load</span>
            <div className="flex items-baseline gap-1">
              <span className={`text-lg font-mono font-bold transition-colors ${cpuLoad > 80 ? 'text-red-400' :
                  cpuLoad > 50 ? 'text-orange-400' :
                    'text-blue-400'
                }`}>
                {cpuLoad.toFixed(0)}
              </span>
              <span className="text-[10px] text-gray-500">%</span>
            </div>
            {/* Mini load bar */}
            <div className="w-full bg-black/40 h-1 rounded-full mt-1.5 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${cpuLoad > 80 ? 'bg-red-500' :
                    cpuLoad > 50 ? 'bg-orange-500' :
                      'bg-blue-500'
                  }`}
                style={{ width: `${Math.min(100, cpuLoad)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Orbit & Velocity Row */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="text-[9px] text-gray-500 uppercase font-bold block mb-0.5">Orbit Alt</span>
            <span className="text-xs font-mono text-blue-300">{altitude.toFixed(1)} km</span>
          </div>
          <div>
            <span className="text-[9px] text-gray-500 uppercase font-bold block mb-0.5">Velocity</span>
            <span className="text-xs font-mono text-blue-300">7.6 km/s</span>
          </div>
        </div>

        {/* Signal & Comms */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="text-[9px] text-gray-500 uppercase font-bold block mb-0.5">Signal Str</span>
            <div className="flex gap-0.5 items-end h-3">
              <div className="w-1 h-1 bg-green-500 rounded-sm"></div>
              <div className="w-1 h-2 bg-green-500 rounded-sm"></div>
              <div className="w-1 h-3 bg-green-500 rounded-sm"></div>
              <div className="w-1 h-3 bg-green-500/30 rounded-sm"></div>
              <span className="text-[8px] text-green-500 ml-1 font-mono uppercase">Strong</span>
            </div>
          </div>
          <div>
            <span className="text-[9px] text-gray-500 uppercase font-bold block mb-0.5">Comm Link</span>
            <span className={`text-[10px] font-mono ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
              {isConnected ? 'ESTABLISHED' : 'LOST'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SystemHealth
