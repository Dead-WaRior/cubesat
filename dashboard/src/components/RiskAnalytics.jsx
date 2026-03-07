import React, { useMemo, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import useDashboardStore from '../store';

/**
 * RiskAnalytics
 * Collision probability timeline with dynamic color:
 *  - Safe: stable green line
 *  - Critical: red spike showing collision window
 */
function RiskAnalytics() {
  const selectedTrackId = useDashboardStore((s) => s.selectedTrackId);
  const setSelectedTrackId = useDashboardStore((s) => s.setSelectedTrackId);
  const pcHistory = useDashboardStore((s) => s.pcHistory);
  const tracks = useDashboardStore((s) => s.tracks);

  useEffect(() => {
    if (!selectedTrackId && tracks.length > 0) {
      setSelectedTrackId(tracks[0].track_id);
    }
  }, [selectedTrackId, tracks, setSelectedTrackId]);

  const activeTrackId = selectedTrackId || (tracks.length > 0 ? tracks[0].track_id : null);

  const { data, maxPc, riskState } = useMemo(() => {
    if (!activeTrackId || !pcHistory[activeTrackId] || pcHistory[activeTrackId].length === 0) {
      return { data: [], maxPc: 0, riskState: 'safe' };
    }

    const points = pcHistory[activeTrackId].map((p, idx) => ({
      name: idx,
      pc: p.pc,
      // Threshold markers for visual reference
      safe: 1e-6,
      warning: 1e-4,
      critical: 1e-3,
    }));

    const max = Math.max(...points.map(p => p.pc));
    let state = 'safe';
    if (max >= 1e-3) state = 'critical';
    else if (max >= 1e-4) state = 'warning';

    return { data: points, maxPc: max, riskState: state };
  }, [activeTrackId, pcHistory]);

  const trackInfo = tracks.find(t => String(t.track_id) === String(activeTrackId));
  const trackLabel = trackInfo ? `D-${String(trackInfo.track_id).padStart(3, '0')}` : '';

  // Dynamic stroke/fill colors based on risk
  const strokeColor = riskState === 'critical' ? '#ef4444'
    : riskState === 'warning' ? '#f59e0b'
      : '#22c55e';

  const gradientId = 'pcGradient';

  if (!activeTrackId || data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-600 font-mono text-[10px] uppercase">
        <span className="animate-pulse">Awaiting Collision Probability Data...</span>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col">
      <div className="flex justify-between items-center mb-2 px-1">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-black text-blue-500/80 uppercase">Probability of Collision Timeline</span>
          {trackLabel && (
            <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded ${riskState === 'critical' ? 'bg-red-500/20 text-red-400' :
                riskState === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-green-500/20 text-green-400'
              }`}>{trackLabel}</span>
          )}
        </div>
        <span className="text-[8px] font-mono text-gray-500">Last 30 seconds per track</span>
      </div>

      <div className="flex-1 min-h-[120px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={strokeColor} stopOpacity={0.4} />
                <stop offset="70%" stopColor={strokeColor} stopOpacity={0.05} />
                <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
            <XAxis dataKey="name" hide />
            <YAxis
              stroke="#475569"
              fontSize={8}
              tickFormatter={(val) => val.toExponential(0)}
              domain={[0, 'auto']}
              scale="log"
              allowDataOverflow
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', fontSize: '9px', borderRadius: '8px' }}
              itemStyle={{ color: strokeColor }}
              labelStyle={{ display: 'none' }}
              formatter={(value) => [value.toExponential(3), 'P(c)']}
            />

            {/* Critical threshold line */}
            <ReferenceLine y={1e-3} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.5}
              label={{ value: 'CRITICAL', position: 'right', fill: '#ef4444', fontSize: 7 }} />
            {/* Warning threshold line */}
            <ReferenceLine y={1e-4} stroke="#f59e0b" strokeDasharray="4 4" strokeOpacity={0.3}
              label={{ value: 'WARNING', position: 'right', fill: '#f59e0b', fontSize: 7 }} />

            <Area
              type="monotone"
              dataKey="pc"
              stroke={strokeColor}
              strokeWidth={2}
              fillOpacity={1}
              fill={`url(#${gradientId})`}
              isAnimationActive={false}
              dot={false}
              activeDot={{ r: 3, fill: strokeColor, stroke: '#fff', strokeWidth: 1 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Risk status bar */}
      <div className="flex items-center gap-3 px-1 mt-1">
        <div className={`flex items-center gap-1.5 text-[9px] font-bold uppercase ${riskState === 'critical' ? 'text-red-400' :
            riskState === 'warning' ? 'text-yellow-400' :
              'text-green-400'
          }`}>
          <div className={`w-1.5 h-1.5 rounded-full ${riskState === 'critical' ? 'bg-red-500 animate-pulse' :
              riskState === 'warning' ? 'bg-yellow-500' :
                'bg-green-500'
            }`} />
          {riskState === 'critical' ? 'CRITICAL COLLISION RISK' :
            riskState === 'warning' ? 'ELEVATED RISK' :
              'SAFE — NOMINAL'}
        </div>
        <span className="text-[8px] text-gray-600 font-mono ml-auto">
          MAX Pc: {maxPc.toExponential(2)}
        </span>
      </div>
    </div>
  );
}

export default RiskAnalytics;
