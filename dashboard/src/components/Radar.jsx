import { useEffect, useRef } from 'react'
import useDashboardStore from '../store'

function Radar() {
    const tracks = useDashboardStore((s) => s.tracks)
    const isSimulating = useDashboardStore((s) => s.isSimulating)
    const canvasRef = useRef(null)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        const width = canvas.width
        const height = canvas.height
        const centerX = width / 2
        const centerY = height / 2

        let animationFrameId
        let angleOffset = 0

        const render = () => {
            // Clear background
            ctx.fillStyle = '#020617'
            ctx.fillRect(0, 0, width, height)

            // Draw radar circles (zones)
            const maxDist = 1000 // 1000 meters max radius conceptually
            const maxRadius = Math.min(width, height) / 2 - 20

            // Zones: Green (outer), Yellow (middle), Red (inner)
            const drawZone = (radiusRatio, color, fillOpacity) => {
                ctx.beginPath()
                ctx.arc(centerX, centerY, maxRadius * radiusRatio, 0, Math.PI * 2)
                ctx.fillStyle = `rgba(${color}, ${fillOpacity})`
                ctx.fill()
                ctx.strokeStyle = `rgba(${color}, 0.5)`
                ctx.lineWidth = 1
                ctx.stroke()
            }

            drawZone(1.0, '34, 197, 94', 0.05)   // Green zone > 500m
            drawZone(0.5, '234, 179, 8', 0.1)     // Yellow zone < 500m
            drawZone(0.2, '239, 68, 68', 0.15)    // Red zone < 200m

            // Radar sweep
            angleOffset = (angleOffset + 0.02) % (Math.PI * 2)
            ctx.beginPath()
            ctx.moveTo(centerX, centerY)
            ctx.arc(centerX, centerY, maxRadius, angleOffset, angleOffset + 0.2)
            ctx.fillStyle = 'rgba(59, 130, 246, 0.3)'
            ctx.fill()

            // Draw crosshairs
            ctx.beginPath()
            ctx.moveTo(centerX, 0)
            ctx.lineTo(centerX, height)
            ctx.moveTo(0, centerY)
            ctx.lineTo(width, centerY)
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)'
            ctx.stroke()

            // Central CubeSat
            ctx.beginPath()
            ctx.arc(centerX, centerY, 4, 0, Math.PI * 2)
            ctx.fillStyle = '#3b82f6'
            ctx.fill()
            ctx.shadowBlur = 10
            ctx.shadowColor = '#3b82f6'

            // Plot debris
            tracks.forEach((track) => {
                // Calculate distance (rough mapping from TCA and velocity)
                const vel = typeof track.vx === 'number' && typeof track.vy === 'number' ? Math.hypot(track.vx, track.vy) : 7.0
                const tca = track.tca_min ?? 5.0
                let dist = Math.max(0, tca * 60 * vel)
                // If simulating, push them further out quickly as a fake effect
                if (isSimulating) {
                    dist += 400
                }

                // Map distance to a radius
                const radius = Math.min(maxRadius, (dist / maxDist) * maxRadius)

                // Make up an angle using the track ID as seed so they spread out
                const angle = (track.track_id * 1.37) % (Math.PI * 2)

                const x = centerX + Math.cos(angle) * radius
                const y = centerY + Math.sin(angle) * radius

                const isCritical = track.alert_level === 'critical'
                const isWarning = track.alert_level === 'warning'

                ctx.beginPath()
                ctx.arc(x, y, isCritical ? 4 : 3, 0, Math.PI * 2)
                ctx.fillStyle = isCritical ? '#ef4444' : isWarning ? '#eab308' : '#22c55e'
                ctx.shadowBlur = 10
                ctx.shadowColor = ctx.fillStyle
                ctx.fill()

                // Distances/TCA label inside radar near the dot (for critical ones)
                if (isCritical || isWarning) {
                    ctx.font = '9px monospace'
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)'
                    ctx.shadowBlur = 0
                    ctx.fillText(`D-${String(track.track_id).padStart(3, '0')}`, x + 6, y - 6)
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.4)'
                    ctx.fillText(`${dist.toFixed(0)}m / ${(tca * 60).toFixed(0)}s`, x + 6, y + 4)
                }
            })

            ctx.shadowBlur = 0

            animationFrameId = requestAnimationFrame(render)
        }

        render()

        return () => cancelAnimationFrame(animationFrameId)
    }, [tracks, isSimulating])

    return (
        <div className="glass-card rounded-xl overflow-hidden shadow-lg mt-4">
            <div className="glass-header">
                <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase flex items-center gap-2">
                    <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.183 1.984-.51 2.87m-3.44-2.04v.001M16.51 18.53A13.93 13.93 0 0016 11M3 11c0 2.453.636 4.75 1.764 6.726" />
                    </svg>
                    Time-to-Collision Radar
                </h2>
            </div>
            <div className="relative w-full flex items-center justify-center bg-[#020617] p-4">
                <canvas ref={canvasRef} width={280} height={280} className="rounded-full shadow-[0_0_30px_rgba(59,130,246,0.1)] border border-white/5" />
                <div className="absolute top-2 left-2 flex flex-col gap-1 text-[8px] font-mono">
                    <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-green-500" /> SAFE ZONE </div>
                    <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-yellow-500" /> WARNING ZONE</div>
                    <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded bg-red-500" /> CRITICAL ZONE</div>
                </div>
            </div>
        </div>
    )
}

export default Radar
