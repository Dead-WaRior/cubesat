import React, { useMemo } from 'react';
import useDashboardStore from '../store';

/**
 * GroundTrack
 * 
 * Visualizes the sub-satellite point and orbital path over a 2D world map.
 * Uses a simplified Mercator projection for the SVG map.
 */
function GroundTrack() {
  const satLla = useDashboardStore((s) => s.satLla);

  // Map dimensions
  const WIDTH = 400;
  const HEIGHT = 200;

  // Convert Lat/Lon to pixel coordinates
  // Lat: 90 (N) to -90 (S) -> 0 to HEIGHT
  // Lon: -180 (W) to 180 (E) -> 0 to WIDTH
  const pos = useMemo(() => {
     if (!satLla) return null;
     const x = ((satLla.lon + 180) * WIDTH) / 360;
     const y = ((90 - satLla.lat) * HEIGHT) / 180;
     return { x, y };
  }, [satLla]);

  return (
    <div className="glass-card rounded-xl overflow-hidden shadow-lg flex flex-col h-full">
      <div className="glass-header">
         <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">Ground Track</h2>
         {satLla && (
             <div className="flex gap-3 text-[10px] font-mono text-blue-400">
                <span>LAT: {satLla.lat.toFixed(2)}°</span>
                <span>LON: {satLla.lon.toFixed(2)}°</span>
             </div>
         )}
      </div>

      <div className="flex-1 relative bg-slate-950 p-2 min-h-[220px]">
        {/* Simple SVG World Map Outline */}
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full h-full opacity-40">
           <rect width={WIDTH} height={HEIGHT} fill="#020617" />
           {/* Placeholder for continent paths - simplified blocks for demo */}
           <path d="M50,40 L120,40 L120,80 L80,100 L40,80 Z" fill="#1e293b" /> {/* N America approx */}
           <path d="M140,40 L240,40 L240,100 L200,120 L160,100 Z" fill="#1e293b" /> {/* Eurasia approx */}
           <path d="M100,100 L140,100 L140,160 L120,180 L80,140 Z" fill="#1e293b" /> {/* S America approx */}
           <path d="M180,100 L220,100 L220,160 L200,180 L160,140 Z" fill="#1e293b" /> {/* Africa approx */}
           <path d="M280,120 L340,120 L340,160 L280,160 Z" fill="#1e293b" /> {/* Australia approx */}
           
           <g className="opacity-20 cyber-grid">
               <line x1="0" y1={HEIGHT/2} x2={WIDTH} y2={HEIGHT/2} stroke="white" strokeWidth="0.5" strokeDasharray="2 2" />
               <line x1={WIDTH/2} y1="0" x2={WIDTH/2} y2={HEIGHT} stroke="white" strokeWidth="0.5" strokeDasharray="2 2" />
           </g>

           {pos && (
               <g>
                  {/* Sat position */}
                  <circle cx={pos.x} cy={pos.y} r="4" fill="#3b82f6" className="animate-pulse" />
                  <circle cx={pos.x} cy={pos.y} r="8" fill="none" stroke="#3b82f6" strokeWidth="0.5" strokeOpacity="0.5" />
                  {/* Crosshair */}
                  <line x1={pos.x - 10} y1={pos.y} x2={pos.x + 10} y2={pos.y} stroke="#3b82f6" strokeWidth="0.5" />
                  <line x1={pos.x} y1={pos.y - 10} x2={pos.x} y2={pos.y + 10} stroke="#3b82f6" strokeWidth="0.5" />
               </g>
           )}
        </svg>

        {!satLla && (
             <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm">
                <span className="text-xs text-gray-500 font-mono tracking-widest animate-pulse">Awaiting GPS Lock...</span>
             </div>
        )}
      </div>

      <div className="px-4 py-2 bg-white/5 border-t border-white/5 flex justify-between text-[10px] text-gray-500 font-mono">
         <span>ALT: {satLla?.alt.toFixed(1) ?? '---'} KM</span>
         <span>ORBIT: LEO-SSO</span>
      </div>
    </div>
  );
}

export default GroundTrack;
