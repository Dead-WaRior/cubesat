import React, { useMemo } from 'react';
import useDashboardStore from '../store';

/**
 * SystemMetricsHUD
 * 
 * Top-level dashboard HUD showing critical mission statistics:
 * Total Tracks, Highest Risk level, and System Uptime.
 */
function SystemMetricsHUD() {
  const tracks = useDashboardStore((s) => s.tracks);
  const alerts = useDashboardStore((s) => s.alerts);
  const isConnected = useDashboardStore((s) => s.isConnected);

  const stats = useMemo(() => {
    const criticalCount = tracks.filter(t => t.alert_level === 'critical').length;
    const warningCount = tracks.filter(t => t.alert_level === 'warning').length;
    const maxPc = tracks.length > 0 ? Math.max(...tracks.map(t => t.pc || 0)) : 0;
    
    return {
       criticalCount,
       warningCount,
       maxPc,
       totalObjects: tracks.length
    }
  }, [tracks]);

  return (
    <div className="flex flex-wrap items-center gap-6 px-1">
      {/* Metric 1: Track Count */}
      <div className="flex flex-col">
          <span className="text-[9px] text-gray-500 uppercase font-bold tracking-widest mb-0.5">Objects in Range</span>
          <div className="flex items-baseline gap-2">
             <span className="text-2xl font-black text-white">{stats.totalObjects}</span>
             <span className="text-[10px] text-blue-500 font-mono">ACTIVE SENSORS</span>
          </div>
      </div>

      {/* Divider */}
      <div className="h-8 w-px bg-white/10 hidden sm:block" />

      {/* Metric 2: Max Pc */}
      <div className="flex flex-col">
          <span className="text-[9px] text-gray-500 uppercase font-bold tracking-widest mb-0.5">Max Collision Prob</span>
          <div className="flex items-baseline gap-2">
             <span className={`text-2xl font-black ${stats.maxPc > 0.01 ? 'text-red-500' : 'text-blue-400'}`}>
                {stats.maxPc.toExponential(2)}
             </span>
             <span className="text-[10px] text-gray-500 font-mono">P(c)</span>
          </div>
      </div>

      {/* Divider */}
      <div className="h-8 w-px bg-white/10 hidden sm:block" />

      {/* Metric 3: Alert Status */}
      <div className="flex flex-col">
          <span className="text-[9px] text-gray-500 uppercase font-bold tracking-widest mb-0.5">Alert Integrity</span>
          <div className="flex items-baseline gap-3">
             <div className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${stats.criticalCount > 0 ? 'bg-red-500 animate-ping' : 'bg-green-500'}`} />
                <span className="text-sm font-bold uppercase text-gray-300">{stats.criticalCount > 0 ? 'CRITICAL' : 'STABLE'}</span>
             </div>
             {stats.warningCount > 0 && <span className="text-[10px] text-amber-500 font-bold">+{stats.warningCount} WRN</span>}
          </div>
      </div>

      {/* Connection HUD - Floating Right Style */}
      <div className="ml-auto hidden lg:flex items-center gap-4 bg-white/5 border border-white/5 rounded-full px-4 py-1.5 backdrop-blur-md">
          <div className="flex flex-col items-end">
              <span className="text-[8px] text-gray-600 uppercase font-black leading-none">Telemetry Link</span>
              <span className={`text-[10px] font-bold ${isConnected ? 'text-blue-400' : 'text-red-500'}`}>
                {isConnected ? 'ENCRYPTED / AES-256' : 'LINK LOST'}
              </span>
          </div>
          <div className={`w-3 h-3 rounded-full border-2 border-black ${isConnected ? 'bg-blue-500 shadow-[0_0_8px_#3b82f6]' : 'bg-red-950'}`} />
      </div>
    </div>
  );
}

export default SystemMetricsHUD;
