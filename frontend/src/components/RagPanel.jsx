import { useEffect, useMemo, useRef } from 'react'
import { Brain } from 'lucide-react'
import Panel from './Panel.jsx'

function Constellation() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const cv = canvasRef.current
    if (!cv) return
    const ctx = cv.getContext('2d')
    let raf
    let t = 0

    const rawNodes = [
      { x: 140, y: 38, r: 6.5, c: '#b91c1c', glow: '#ef4444', isCore: true, fx: 0.8, fy: 1.1, ax: 1.2, ay: 1.0, ph: 0 },
      { x: 153, y: 15, r: 4.5, c: '#b91c1c', glow: '#ef4444', isCore: false, fx: 1.1, fy: 0.9, ax: 2.2, ay: 2.0, ph: 1.2 },
      { x: 115, y: 22, r: 4.2, c: '#d97706', glow: '#f59e0b', isCore: false, fx: 0.9, fy: 1.3, ax: 2.5, ay: 2.2, ph: 2.4 },
      { x: 125, y: 6, r: 3.8, c: '#78350f', glow: '#d97706', isCore: false, fx: 1.3, fy: 1.0, ax: 2.0, ay: 2.0, ph: 3.1 },
      { x: 96, y: 9, r: 3.5, c: '#573014', glow: '#78350f', isCore: false, fx: 0.8, fy: 1.2, ax: 2.2, ay: 1.8, ph: 4.0 },
      { x: 182, y: 12, r: 3.5, c: '#573014', glow: '#78350f', isCore: false, fx: 1.2, fy: 0.8, ax: 2.0, ay: 2.4, ph: 0.8 },
      { x: 78, y: 34, r: 4.2, c: '#d97706', glow: '#f59e0b', isCore: false, fx: 1.0, fy: 1.1, ax: 2.5, ay: 2.0, ph: 5.2 },
      { x: 102, y: 44, r: 3.6, c: '#573014', glow: '#78350f', isCore: false, fx: 1.2, fy: 0.9, ax: 2.0, ay: 2.2, ph: 2.1 },
      { x: 126, y: 56, r: 4.2, c: '#d97706', glow: '#f59e0b', isCore: false, fx: 0.9, fy: 1.2, ax: 2.2, ay: 2.0, ph: 3.7 },
      { x: 152, y: 66, r: 4.2, c: '#d97706', glow: '#f59e0b', isCore: false, fx: 1.1, fy: 1.0, ax: 2.0, ay: 2.5, ph: 1.8 },
      { x: 170, y: 34, r: 4.2, c: '#d97706', glow: '#f59e0b', isCore: false, fx: 1.0, fy: 1.3, ax: 2.4, ay: 2.0, ph: 4.5 },
      { x: 200, y: 40, r: 4.2, c: '#d97706', glow: '#f59e0b', isCore: false, fx: 0.8, fy: 1.1, ax: 2.2, ay: 2.2, ph: 0.5 },
      { x: 174, y: 56, r: 3.8, c: '#573014', glow: '#78350f', isCore: false, fx: 1.2, fy: 0.9, ax: 2.0, ay: 2.0, ph: 3.3 },
      { x: 190, y: 62, r: 3.5, c: '#573014', glow: '#78350f', isCore: false, fx: 0.9, fy: 1.2, ax: 2.0, ay: 2.2, ph: 2.8 },
      { x: 108, y: 64, r: 4.2, c: '#d97706', glow: '#f59e0b', isCore: false, fx: 1.1, fy: 1.0, ax: 2.2, ay: 2.0, ph: 4.9 },
    ]

    const edges = [
      [0, 1], [0, 2], [0, 8], [0, 9], [0, 10], [0, 12],
      [1, 2], [1, 10], [1, 5],
      [2, 3], [2, 4], [2, 6], [2, 7],
      [6, 7], [7, 8], [7, 14], [8, 14], [8, 9],
      [9, 12], [10, 11], [10, 12], [11, 12], [11, 13], [12, 13]
    ]

    const particles = edges.slice(0, 10).map((edge, i) => ({
      edge,
      progress: (i * 0.15) % 1,
      speed: 0.005 + (i % 3) * 0.003
    }))

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
      t += 0.025

      const scaleX = W / 270
      const scaleY = H / 80

      const curNodes = rawNodes.map((n) => {
        const dx = Math.sin(t * n.fx + n.ph) * n.ax
        const dy = Math.cos(t * n.fy + n.ph) * n.ay
        return {
          x: (n.x + dx) * scaleX,
          y: (n.y + dy) * scaleY,
          r: n.r * Math.min(scaleX, scaleY),
          c: n.c,
          glow: n.glow,
          isCore: n.isCore,
        }
      })

      // Draw connection lines
      ctx.lineWidth = 1
      edges.forEach(([a, b]) => {
        const na = curNodes[a]
        const nb = curNodes[b]
        ctx.strokeStyle = 'rgba(146, 64, 14, 0.45)'
        ctx.beginPath()
        ctx.moveTo(na.x, na.y)
        ctx.lineTo(nb.x, nb.y)
        ctx.stroke()
      })

      // Draw traveling vector pulses
      particles.forEach((p) => {
        p.progress = (p.progress + p.speed) % 1
        const na = curNodes[p.edge[0]]
        const nb = curNodes[p.edge[1]]
        const px = na.x + (nb.x - na.x) * p.progress
        const py = na.y + (nb.y - na.y) * p.progress
        ctx.beginPath()
        ctx.arc(px, py, 1.8, 0, Math.PI * 2)
        ctx.fillStyle = '#fef08a'
        ctx.shadowColor = '#f59e0b'
        ctx.shadowBlur = 6
        ctx.fill()
        ctx.shadowBlur = 0
      })

      // Draw nodes
      curNodes.forEach((n) => {
        const pulseR = n.isCore ? n.r + Math.sin(t * 3) * 1.2 : n.r + Math.sin(t * 2 + n.x) * 0.4
        ctx.beginPath()
        ctx.arc(n.x, n.y, pulseR, 0, Math.PI * 2)
        ctx.fillStyle = n.c
        ctx.shadowColor = n.glow
        ctx.shadowBlur = n.isCore ? 10 : 5
        ctx.fill()
        ctx.shadowBlur = 0
      })

      raf = requestAnimationFrame(draw)
    }

    draw()
    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [])

  return (
    <div className="relative h-[68px] w-full overflow-hidden">
      <canvas ref={canvasRef} className="h-full w-full" />
    </div>
  )
}

export default function RagPanel({ rag }) {
  const kb = rag.points.bloodstrike_knowledge ?? 0
  const online = rag.status === 'online'
  return (
    <Panel
      title="Hybrid RAG Context (Qdrant Cloud)"
      id="E"
      icon={<span className="text-[13px] leading-none">🧠</span>}
      bodyClass="flex flex-col justify-between p-2"
    >
      <Constellation />
      <div className="space-y-0.5 text-[8px] leading-snug text-slate-200">
        <div>
          Active Knowledge: <code className="text-slate-100">`bloodstrike_knowledge`</code> (AK47, INP-9, M4A1)
        </div>
        <div>
          Points:{' '}
          <span className="font-semibold text-safe">
            {kb} / {rag.total} {online ? 'Online' : 'Offline'}
          </span>
        </div>
        <div>
          Memory: <code className="text-slate-100">`player_memory`</code> Chronological history loaded.
        </div>
      </div>
    </Panel>
  )
}
