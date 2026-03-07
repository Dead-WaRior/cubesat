import useDashboardStore from '../store'

function RiskGauge() {
    const tracks = useDashboardStore((s) => s.tracks)
    const isSimulating = useDashboardStore((s) => s.isSimulating)

    let riskLevel = 'Safe Status'
    let colorClass = 'text-green-500'
    let bgClass = 'bg-green-500'
    let shadowClass = 'shadow-[0_0_15px_#22c55e]'
    let rotation = -70 + Math.random() * 20

    const hasCritical = tracks.some(t => t.alert_level === 'critical') && !isSimulating
    const hasWarning = tracks.some(t => t.alert_level === 'warning') && !isSimulating

    if (hasCritical) {
        riskLevel = 'Critical'
        colorClass = 'text-red-500'
        bgClass = 'bg-red-500'
        shadowClass = 'shadow-[0_0_20px_#ef4444]'
        rotation = 50 + Math.random() * 20
    } else if (hasWarning) {
        riskLevel = 'Medium Risk'
        colorClass = 'text-yellow-500'
        bgClass = 'bg-yellow-500'
        shadowClass = 'shadow-[0_0_15px_#eab308]'
        rotation = -10 + Math.random() * 20
    }

    return (
        <div className="glass-card rounded-xl overflow-hidden shadow-lg mt-4 h-48 flex flex-col relative">
            <div className="glass-header z-10">
                <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">
                    Risk Indicator
                </h2>
            </div>

            <div className="flex-1 flex flex-col justify-center items-center relative bottom-2">
                <div className="relative w-28 h-28">
                    {/* Gauge Background */}
                    <svg className="w-full h-full" viewBox="0 0 100 50">
                        <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#1f2937" strokeWidth="12" strokeLinecap="round" />

                        {/* Safe Zone */}
                        <path d="M 10 50 A 40 40 0 0 1 30 15" fill="none" stroke="#22c55e" strokeWidth="12" strokeLinecap="round" strokeDasharray="60" strokeDashoffset="0" opacity="0.4" />
                        {/* Warning Zone */}
                        <path d="M 30 15 A 40 40 0 0 1 70 15" fill="none" stroke="#eab308" strokeWidth="12" strokeDasharray="60" strokeDashoffset="0" opacity="0.4" />
                        {/* Critical Zone */}
                        <path d="M 70 15 A 40 40 0 0 1 90 50" fill="none" stroke="#ef4444" strokeWidth="12" strokeLinecap="round" strokeDasharray="60" strokeDashoffset="0" opacity="0.4" />
                    </svg>

                    {/* Needle */}
                    <div
                        className="absolute bottom-[-10px] left-1/2 w-1.5 h-16 bg-white origin-bottom transition-transform duration-1000 ease-out"
                        style={{ transform: `translateX(-50%) rotate(${rotation}deg)`, borderRadius: '4px 4px 0 0' }}
                    >
                        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[3px] border-l-transparent border-r-[3px] border-r-transparent border-b-[8px] border-b-gray-200 -mt-2"></div>
                    </div>

                    {/* Center Hub */}
                    <div className={`absolute bottom-[-16px] left-1/2 -translate-x-1/2 w-8 h-8 rounded-full border-4 border-gray-900 ${bgClass} ${shadowClass} transition-colors duration-1000`}></div>
                </div>

                <div className={`mt-2 font-black uppercase text-xl ${colorClass} tracking-widest transition-colors duration-1000 animate-pulse`}>
                    {riskLevel}
                </div>
            </div>

            {/* Decorative Grid */}
            <div className="absolute inset-x-0 bottom-0 h-8 opacity-20 pointer-events-none text-white/10 cyber-grid" />
        </div>
    )
}

export default RiskGauge
