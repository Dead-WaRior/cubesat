import useWebSocket from './hooks/useWebSocket'
import LiveFeed from './components/LiveFeed'
import TracksTable from './components/TracksTable'
import RiskTimeline from './components/RiskTimeline'
import AlertFeed from './components/AlertFeed'
import ManeuverPanel from './components/ManeuverPanel'
import SystemHealth from './components/SystemHealth'
import CriticalModal from './components/CriticalModal'
import useDashboardStore from './store'

/**
 * App
 *
 * Root component.  Establishes the WebSocket connection and renders the
 * full three-column dashboard layout.
 */
function App() {
  const { isConnected } = useWebSocket()
  const lastUpdate = useDashboardStore((s) => s.lastUpdate)

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* ── Top header bar ─────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-4 sm:px-6 py-3 bg-gray-900 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xl select-none" role="img" aria-label="satellite">🛰️</span>
          <h1 className="text-sm sm:text-base font-bold tracking-wide text-gray-100">
            CubeSat Collision Prediction System
          </h1>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {lastUpdate && (
            <span className="hidden sm:block text-gray-500">
              Last update: {new Date(lastUpdate).toLocaleTimeString()}
            </span>
          )}
          <span className="flex items-center gap-1.5">
            <span
              className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${
                isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}
            />
            <span className={isConnected ? 'text-green-400' : 'text-red-400'}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </span>
        </div>
      </header>

      {/* ── Main content area ───────────────────────────────────────────── */}
      <main className="flex-1 p-3 sm:p-4 overflow-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 max-w-screen-2xl mx-auto">

          {/* Left column: Live feed + System health */}
          <div className="flex flex-col gap-4">
            <LiveFeed />
            <SystemHealth />
          </div>

          {/* Middle column: Tracks table + Maneuver panel */}
          <div className="flex flex-col gap-4">
            <TracksTable />
            <ManeuverPanel />
          </div>

          {/* Right column: Risk timeline + Alert feed */}
          <div className="flex flex-col gap-4">
            <RiskTimeline />
            <AlertFeed />
          </div>

        </div>
      </main>

      {/* ── Critical alert modal overlay ────────────────────────────────── */}
      <CriticalModal />
    </div>
  )
}

export default App
