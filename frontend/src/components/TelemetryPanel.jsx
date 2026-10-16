import { useEffect, useRef } from 'react'
import { Activity } from 'lucide-react'
import Panel from './Panel.jsx'

/** Matrix-style green digital telemetry canvas */
export default function TelemetryPanel({ hw }) {
  const ref = useRef(null)
  const live = useRef(hw)
  live.current = hw

  useEffect(() => {
    const cv = ref.current
    const ctx = cv.getContext('2d')
    let raf
    let t = 0
    const chars = ['0', '1', '8', '9', 'B', 'D', 'S', 'H', '0', '5', '0']

    const resize = () => {
      const r = cv.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      cv.width = r.width * dpr
      cv.height = r.height * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(cv)

    const draw = () => {
      const { width: W, height: H } = cv.getBoundingClientRect()
      ctx.clearRect(0, 0, W, H)
      t += 0.035

      const colW = 7
      const cols = Math.floor(W / colW)
      const cy = H * 0.42
      const rowH = 7.5

      ctx.font = 'bold 7px "JetBrains Mono", monospace'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'

      for (let i = 0; i < cols; i++) {
        const x = (i + 0.5) * colW
        // Multi-frequency wave pattern
        const env = Math.sin(i * 0.09 + t) * Math.cos(i * 0.04 - t * 0.5)
        const wave = Math.abs(env) * (H * 0.38) + 4
        const rowsCount = Math.floor(wave / rowH)

        // Center baseline character
        ctx.fillStyle = '#4ade80'
        ctx.shadowColor = '#22c55e'
        ctx.shadowBlur = 4
        ctx.fillText('0', x, cy)
        ctx.shadowBlur = 0

        // Characters going up and down
        for (let j = 1; j <= rowsCount; j++) {
          const charUp = chars[(i * 3 + j + Math.floor(t * 2)) % chars.length]
          const charDown = chars[(i * 5 + j + Math.floor(t * 3)) % chars.length]
          const alpha = Math.max(0.2, 1 - j / (rowsCount + 1))
          
          ctx.fillStyle = `rgba(74, 222, 128, ${alpha})`
          ctx.fillText(charUp, x, cy - j * rowH)
          ctx.fillText(charDown, x, cy + j * rowH)
        }
      }

      raf = requestAnimationFrame(draw)
    }
    draw()
    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [])

  return (
    <Panel
      title="Telemetry"
      icon={<Activity className="h-4 w-4 text-slate-400" />}
      bodyClass="relative flex flex-col justify-between p-1.5"
    >
      <div className="pointer-events-none absolute inset-x-2 top-1 flex justify-between font-mono text-[6.5px] text-slate-500">
        <span>Nsec=212 ms</span>
        <span>-70C</span>
      </div>
      <canvas ref={ref} className="h-full w-full" />
      <div className="pointer-events-none relative inset-x-0 bottom-0 flex items-center justify-between px-1 font-mono text-[7px] text-slate-400">
        <span>8X</span>
        <div className="flex items-center gap-1">
          <div className="relative flex items-center">
            <span className="h-[2px] w-8 rounded bg-red-600/80" />
            <span className="h-2 w-[1.5px] bg-red-500" />
          </div>
          <span className="text-[7.5px] text-slate-300">006</span>
          <span className="h-[2px] w-8 rounded bg-safe/80" />
        </div>
        <span className="text-safe">7X</span>
      </div>
    </Panel>
  )
}
