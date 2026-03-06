import useWebSocket from './hooks/useWebSocket'
import LiveFeed from './components/LiveFeed'
import GroundTrack from './components/GroundTrack'
import TracksTable from './components/TracksTable'
import RiskTimeline from './components/RiskTimeline'
import AlertFeed from './components/AlertFeed'
import SystemMetricsHUD from './components/SystemMetricsHUD'
import ManeuverPanel from './components/ManeuverPanel'
import OrbitalView from './components/OrbitalView'
import SystemHealth from './components/SystemHealth'
import ObjectInspector from './components/ObjectInspector'
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
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col mesh-gradient scrollbar-thin">
      <div className="fixed inset-0 cyber-grid opacity-10 pointer-events-none" />
      {/* ── Top header bar ─────────────────────────────────────────────── */}
      <header className="flex flex-col px-4 sm:px-6 py-4 bg-gray-900/80 border-b border-white/5 backdrop-blur-xl flex-shrink-0 z-10 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-blue-600 rounded-lg shadow-lg shadow-blue-900/20">
               <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 21l-8-4.5v-9L12 3l8 4.5v9L12 21z" />
               </svg>
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tighter text-white uppercase leading-none">
                CubeSat <span className="text-blue-500 italic">Collision Control</span>
              </h1>
              <p className="text-[10px] text-gray-500 font-mono tracking-widest mt-1">SENTINEL-1 AUTO-SURVEILLANCE UNIT</p>
            </div>
          </div>
          <div className="text-right">
             <p className="text-[10px] text-gray-500 uppercase font-bold tracking-widest mb-0.5">Last Transmission</p>
             <p className="text-xs font-mono text-gray-300">
               {lastUpdate ? new Date(lastUpdate).toISOString() : 'AWAITING LINK...'}
             </p>
          </div>
        </div>
        
        {/* Real-time Stat HUD */}
        <SystemMetricsHUD />
      </header>

      {/* ── Main content area ───────────────────────────────────────────── */}
      <main className="flex-1 p-3 sm:p-4 overflow-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 max-w-screen-2xl mx-auto">

          {/* Left column: Live feed + System health */}
          <div className="flex flex-col gap-4">
            <LiveFeed />
            <SystemHealth />
          </div>

          {/* Middle column: Orbital View + Ground Track + Maneuver panel */}
          <div className="flex flex-col gap-4">
            <OrbitalView />
            <GroundTrack />
            <ManeuverPanel />
          </div>

          {/* Right column: Tracks table + Risk timeline + Alert feed */}
          <div className="flex flex-col gap-4">
            <TracksTable />
            <RiskTimeline />
            <AlertFeed />
          </div>

        </div>
      </main>

      {/* ── Overlays ─────────────────────────────────────────────────────── */}
      <ObjectInspector />
      <CriticalModal />
    </div>
  )
}

export default App
