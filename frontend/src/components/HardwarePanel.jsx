import { ShieldCheck } from 'lucide-react'
import Panel from './Panel.jsx'

function Bar({ label, value, text, color }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-1 font-mono text-[9px] text-slate-200">
        <span className="font-semibold">{label}:</span>
        <span>{text}</span>
      </div>
      <div className="mt-0.5 h-[3px] overflow-hidden rounded bg-[#1a2133]">
        <div
          className="h-full rounded transition-[width] duration-700"
          style={{ width: `${Math.min(100, value)}%`, background: color, boxShadow: `0 0 8px ${color}` }}
        />
      </div>
    </div>
  )
}

function Ring({ pct }) {
  const r = 40
  const c = 2 * Math.PI * r
  return (
    <svg viewBox="0 0 100 100" className="h-[56px] w-[56px] shrink-0 -rotate-90">
      <defs>
        <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#f43f5e" />
          <stop offset="100%" stopColor="#ef4444" />
        </linearGradient>
      </defs>
      <circle cx="50" cy="50" r={r} fill="none" stroke="#3a1620" strokeWidth="9" />
      <circle
        cx="50"
        cy="50"
        r={r}
        fill="none"
        stroke="url(#ringGrad)"
        strokeWidth="9"
        strokeLinecap="butt"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - pct / 100)}
        style={{ transition: 'stroke-dashoffset .7s', filter: 'drop-shadow(0 0 4px rgba(244,63,94,.8))' }}
      />
      <text
        x="50"
        y="50"
        transform="rotate(90 50 50)"
        textAnchor="middle"
        dominantBaseline="central"
        fill="#e2e8f0"
        fontSize="14"
        fontFamily="Rajdhani, sans-serif"
        fontWeight="700"
      >
        CP%
      </text>
    </svg>
  )
}

export default function HardwarePanel({ hw }) {
  const safe = hw.is_safe_to_play
  const gb = (hw.ram_used_mb / 1024).toFixed(1)
  const totalGb = Math.round(hw.ram_total_mb / 1024)
  const cpuModel = hw.cpu_name ? hw.cpu_name.replace('w/ Radeon Vega Mobile Gfx', '').trim() : 'AMD Ryzen 5 PRO 3500U'
  const gpuModel = hw.gpu_name || 'AMD Radeon(TM) Vega 8 Graphics'

  return (
    <Panel
      title="Live Hardware Safety Advisor"
      id="A"
      icon={<ShieldCheck className="h-4 w-4 text-gold" />}
      bodyClass="p-2 flex flex-col justify-between"
    >
      <div
        className={`rounded border py-1 text-center font-head text-[10px] font-bold tracking-wide ${
          safe ? 'border-safe/70 bg-safe/10 text-safe' : 'border-danger/70 bg-danger/10 text-red-300'
        }`}
      >
        {hw.safety_badge}
      </div>

      <div className="mt-2 space-y-0.5 rounded border border-cyan-500/25 bg-cyan-950/25 px-2 py-1 font-mono text-[8px]">
        <div className="flex items-center justify-between text-slate-300">
          <span className="text-slate-400">CPU:</span>
          <span className="font-semibold text-cyan-300 truncate max-w-[160px]" title={cpuModel}>
            {cpuModel}
          </span>
        </div>
        <div className="flex items-center justify-between text-slate-300">
          <span className="text-slate-400">GPU:</span>
          <span className="font-semibold text-rose-300 truncate max-w-[160px]" title={gpuModel}>
            {gpuModel}
          </span>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-3">
        <Ring pct={hw.cpu_pct} />
        <div className="min-w-0 flex-1 space-y-1.5">
          <Bar label="CPU" value={hw.cpu_pct} text={`${Math.round(hw.cpu_pct)}%`} color="#ef4444" />
          <Bar
            label="RAM"
            value={hw.ram_pct}
            text={`${gb}GB / ${totalGb}GB (${Math.round(hw.ram_pct)}%)`}
            color="#f59e0b"
          />
          <Bar label="GPU" value={hw.gpu_pct} text={`${Math.round(hw.gpu_pct)}%`} color="#f59e0b" />
        </div>
      </div>
    </Panel>
  )
}
