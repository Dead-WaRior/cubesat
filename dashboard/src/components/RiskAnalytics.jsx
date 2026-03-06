import React, { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import useDashboardStore from '../store';

/**
 * RiskAnalytics
 * Visualizes the probability of collision (Pc) trend for a selected track.
 */
function RiskAnalytics() {
  const selectedTrackId = useDashboardStore((s) => s.selectedTrackId);
  const pcHistory = useDashboardStore((s) => s.pcHistory);

  const data = useMemo(() => {
    if (!selectedTrackId || !pcHistory[selectedTrackId]) return [];
    
    // Transform pcHistory into chart-friendly format
    // Each point is { timestamp, pc }
    return pcHistory[selectedTrackId].map((p, idx) => ({
      name: idx,
      pc: p.pc,
      pcDisplay: p.pc.toExponential(2)
    }));
  }, [selectedTrackId, pcHistory]);

  if (!selectedTrackId || data.length === 0) {
      return (
          <div className="flex flex-col items-center justify-center h-full text-gray-600 font-mono text-[10px] uppercase">
              <span className="animate-pulse">Awaiting Historical Convergence Data...</span>
          </div>
      );
  }

  return (
    <div className="h-full w-full flex flex-col">
      <div className="flex justify-between items-center mb-2 px-1">
          <span className="text-[9px] font-black text-blue-500/80 uppercase">Probability Convergence (P(c))</span>
          <span className="text-[8px] font-mono text-gray-500">LAST 30 SECONDS</span>
      </div>
      
      <div className="flex-1 min-h-[120px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorPc" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
            <XAxis dataKey="name" hide />
            <YAxis 
                stroke="#475569" 
                fontSize={8} 
                tickFormatter={(val) => val.toExponential(0)}
                domain={[0, 'auto']}
            />
            <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', fontSize: '9px' }}
                itemStyle={{ color: '#ef4444' }}
                labelStyle={{ display: 'none' }}
                formatter={(value) => [value.toExponential(3), 'P(c)']}
            />
            <Area 
                type="monotone" 
                dataKey="pc" 
                stroke="#ef4444" 
                strokeWidth={2}
                fillOpacity={1} 
                fill="url(#colorPc)" 
                isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default RiskAnalytics;
