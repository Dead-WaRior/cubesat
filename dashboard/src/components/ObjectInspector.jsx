import React, { useMemo } from 'react';
import useDashboardStore from '../store';
import RiskAnalytics from './RiskAnalytics';

/**
 * ObjectInspector
 * 
 * A sliding sidebar that provides deep-dive telemetry and analysis
 * for a selected debris track.
 */
function ObjectInspector() {
  const { tracks, selectedTrackId, setSelectedTrackId, alerts, setIsSimulating, isSimulating, satPath, setHypotheticalPath } = useDashboardStore((s) => ({
    tracks: s.tracks,
    selectedTrackId: s.selectedTrackId,
    setSelectedTrackId: s.setSelectedTrackId,
    alerts: s.alerts,
    setIsSimulating: s.setIsSimulating,
    isSimulating: s.isSimulating,
    satPath: s.satPath,
    setHypotheticalPath: s.setHypotheticalPath,
  }));

  const track = useMemo(() => 
    tracks.find(t => String(t.track_id) === String(selectedTrackId)),
  [tracks, selectedTrackId]);

  const activeAlert = useMemo(() => 
    alerts.find(a => String(a.track_id) === String(selectedTrackId)),
  [alerts, selectedTrackId]);

  if (!selectedTrackId) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 glass-card border-l border-white/10 z-50 flex flex-col shadow-2xl animate-in slide-in-from-right duration-300">
      <div className="glass-header">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${track ? 'bg-green-500' : 'bg-red-500'}`} />
          <h2 className="text-sm font-bold tracking-widest uppercase">Object Inspector</h2>
        </div>
        <button 
          onClick={() => setSelectedTrackId(null)}
          className="text-gray-500 hover:text-white transition-colors p-1"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {!track ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <svg className="w-12 h-12 text-gray-700 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.172 9.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-gray-400 text-sm italic">Track #{selectedTrackId} is no longer in field of view</p>
            <button 
                onClick={() => setSelectedTrackId(null)}
                className="mt-4 text-xs text-blue-400 hover:underline"
            >
                Close Inspector
            </button>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
          {/* Header info */}
          <div className="mb-8">
            <div className="flex justify-between items-end mb-1">
              <span className="text-[10px] text-blue-400 font-mono uppercase tracking-tighter">Satellite ID</span>
              <span className="text-xs font-mono text-gray-500">v1.2.0-stable</span>
            </div>
            <h1 className="text-3xl font-black text-white tracking-tight">DEBRIS-#{track.track_id}</h1>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 gap-3 mb-8">
            <div className="p-3 bg-white/5 rounded-lg border border-white/5">
              <p className="text-[10px] text-gray-500 uppercase mb-1">Confidence</p>
              <p className="text-lg font-mono font-bold text-blue-400">{(track.confidence * 100).toFixed(1)}%</p>
            </div>
            <div className="p-3 bg-white/5 rounded-lg border border-white/5">
              <p className="text-[10px] text-gray-500 uppercase mb-1">Persistence</p>
              <p className="text-lg font-mono font-bold text-gray-200">{track.age_frames} fr</p>
            </div>
          </div>

          {/* ECI Vectors */}
          <section className="mb-8">
            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3 border-b border-white/5 pb-1">State Vectors (ECI)</h3>
            <div className="space-y-4">
               <div>
                  <p className="text-[10px] text-gray-500 mb-1 italic">Position (km)</p>
                  <div className="grid grid-cols-3 gap-2 font-mono text-xs">
                    <div className="bg-black/40 p-2 rounded text-blue-300"><span className="text-gray-600 mr-2">X</span>{track.x?.toFixed(4)}</div>
                    <div className="bg-black/40 p-2 rounded text-blue-300"><span className="text-gray-600 mr-2">Y</span>{track.y?.toFixed(4)}</div>
                    <div className="bg-black/40 p-2 rounded text-blue-300"><span className="text-gray-600 mr-2">Z</span>{(track.z ?? 0).toFixed(4)}</div>
                  </div>
               </div>
               <div>
                  <p className="text-[10px] text-gray-500 mb-1 italic">Velocity (km/s)</p>
                  <div className="grid grid-cols-3 gap-2 font-mono text-xs">
                    <div className="bg-black/40 p-2 rounded text-amber-300"><span className="text-gray-600 mr-2">VX</span>{track.vx?.toFixed(5)}</div>
                    <div className="bg-black/40 p-2 rounded text-amber-300"><span className="text-gray-600 mr-2">VY</span>{track.vy?.toFixed(5)}</div>
                    <div className="bg-black/40 p-2 rounded text-amber-300"><span className="text-gray-600 mr-2">VZ</span>{(track.vz ?? 0).toFixed(5)}</div>
                  </div>
               </div>
            </div>
          </section>

          {/* Risk Profile */}
          <section className="mb-8">
               <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3 border-b border-white/5 pb-1">Conjunction Analysis</h3>
               <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-4">
                  <div className="flex justify-between mb-4">
                    <div>
                        <p className="text-[10px] text-blue-400 uppercase mb-0.5">Miss Distance</p>
                        <p className="text-2xl font-bold">{track.miss_distance_km?.toFixed(3) ?? '??'} <span className="text-xs font-normal text-gray-500 italic">km</span></p>
                    </div>
                    <div className="text-right">
                        <p className="text-[10px] text-blue-400 uppercase mb-0.5">Pc Estimate</p>
                        <p className="text-2xl font-mono font-bold">{track.pc?.toExponential(2) ?? '0.00e+0'}</p>
                    </div>
                  </div>
                  
                  {activeAlert && (
                      <div className={`p-3 rounded-lg border flex items-start gap-3 ${
                          activeAlert.alert_level === 'critical' ? 'bg-red-500/10 border-red-500/30' : 'bg-amber-500/10 border-amber-500/30'
                      }`}>
                          <div className={`mt-1 w-2 h-2 rounded-full shrink-0 ${
                             activeAlert.alert_level === 'critical' ? 'bg-red-500 animate-ping' : 'bg-amber-500'
                          }`} />
                          <div>
                            <p className="text-[10px] font-bold uppercase text-white mb-0.5">{activeAlert.alert_level} ALERT ACTIVE</p>
                            <p className="text-[11px] text-gray-300 leading-tight">{activeAlert.recommended_action}</p>
                          </div>
                      </div>
                  )}
               </div>
          </section>

          {/* Risk Trends Analytics */}
          <section className="mb-4">
              <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3 border-b border-white/5 pb-1">Historical Analytics</h3>
              <div className="h-32 bg-black/40 rounded border border-white/5 p-4 flex flex-col justify-center relative overflow-hidden">
                <div className="absolute inset-0 cyber-grid opacity-10" />
                <RiskAnalytics />
              </div>
          </section>
        </div>
      )}

      {/* Footer Actions */}
      <div className="p-4 border-t border-white/10 bg-black/20 grid grid-cols-2 gap-3">
          <button className="py-2 px-4 bg-gray-800 hover:bg-gray-700 text-white rounded text-[10px] uppercase font-bold transition-all border border-white/5">
              Reset ID
          </button>
          <button 
            onClick={() => {
                if (!isSimulating) {
                    const safetyPath = satPath.map(p => ({ x: p.x * 1.05, y: p.y * 1.05, z: p.z * 1.05 }));
                    setHypotheticalPath(safetyPath);
                    setIsSimulating(true);
                } else {
                    setIsSimulating(false);
                }
            }}
            className={`py-2 px-4 rounded text-[10px] uppercase font-bold transition-all ${
                isSimulating ? 'bg-blue-500 text-white shadow-blue-500/40' : 'bg-blue-600 hover:bg-blue-500 text-white'
            }`}
          >
              {isSimulating ? 'SIM ACTIVE' : 'SIM Maneuver'}
          </button>
      </div>
    </div>
  );
}

export default ObjectInspector;
