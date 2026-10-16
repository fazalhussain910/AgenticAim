import { Gamepad2, LayoutDashboard, Mic, History, Box, Settings } from 'lucide-react'

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'voice', label: 'Voice Coach', icon: Mic },
  { id: 'history', label: 'History & Telemetry', icon: History },
  { id: 'qdrant', label: 'Qdrant Vector DB', icon: Box },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export function Header({ hw, online }) {
  const safe = hw.is_safe_to_play
  const cpuShort = hw.cpu_name ? hw.cpu_name.replace('w/ Radeon Vega Mobile Gfx', '').replace('PRO', '').trim() : 'Ryzen 5 3500U'
  const gpuShort = hw.gpu_name ? hw.gpu_name.replace('Graphics', '').replace('(TM)', '').trim() : 'Vega 8'

  return (
    <header className="flex h-[42px] shrink-0 items-center justify-between border-b border-line bg-bg2/80 px-3 backdrop-blur sm:px-5">
      <div className="flex items-center gap-2">
        <div className="relative flex h-7 w-7 items-center justify-center">
          <img
            src="/app_logo.png"
            alt="AgenticAim Logo"
            className="h-7 w-7 rounded object-contain drop-shadow-[0_0_8px_rgba(244,63,94,0.6)]"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
              const fallback = e.currentTarget.parentElement?.querySelector('.fallback-icon')
              if (fallback) fallback.style.display = 'block'
            }}
          />
          <Gamepad2 className="fallback-icon h-6 w-6 text-rose" strokeWidth={1.8} style={{ display: 'none' }} />
        </div>
        <div className="leading-tight">
          <div className="font-head text-[17px] font-bold tracking-wide text-white">AgenticAim</div>
          <div className="text-[8px] text-slate-400">AMD Developer Hackathon III Project</div>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <div className="hidden md:flex items-center gap-1.5 rounded border border-rose/30 bg-rose/10 px-2.5 py-0.5 font-mono text-[9px] font-bold text-rose-300">
          <span className="h-1.5 w-1.5 rounded-full bg-rose-400 animate-pulse" />
          ⚡ {cpuShort.toUpperCase()} • {gpuShort.toUpperCase()}
        </div>

        <div
          className={`flex items-center gap-1.5 rounded-md border px-2 py-1 font-head text-[10px] font-bold tracking-wide sm:px-3 ${
            safe ? 'glow-safe border-safe/70 bg-safe/10 text-safe' : 'glow-unsafe'
          }`}
        >
          <span className={`h-2 w-2 rounded-full ${safe ? 'bg-safe' : 'bg-danger blink'}`} />
          SYSTEM STATUS: {safe ? '[✅ SAFE TO PLAY]' : '[⚠️ UNSAFE]'}
        </div>
        <div className="hidden sm:block"><SignalBars /></div>
      </div>
    </header>
  )
}

function SignalBars() {
  return (
    <div className="flex h-5 items-end gap-[2px]" aria-label="signal">
      {[6, 9, 13, 17].map((h, i) => (
        <span key={i} className="w-[3px] rounded-sm bg-safe" style={{ height: h }} />
      ))}
    </div>
  )
}

export function Sidebar({ active, onChange }) {
  return (
    <aside className="hidden w-[136px] shrink-0 flex-col justify-between border-r border-line bg-bg2/60 py-2 md:flex">
      <nav className="flex flex-col gap-1 px-1">
        {NAV.map(({ id, label, icon: Icon }) => {
          const on = id === active
          return (
            <button
              key={id}
              onClick={() => onChange(id)}
              className={`group relative flex items-center gap-2 rounded px-2 py-2 text-left text-[10px] font-medium transition-colors ${
                on
                  ? 'bg-slate-500/20 text-white'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              }`}
            >
              {on && <span className="absolute inset-y-1 left-0 w-[3px] rounded bg-danger" />}
              <Icon className={`h-[14px] w-[14px] shrink-0 ${on ? 'text-rose' : ''}`} strokeWidth={1.8} />
              {label}
            </button>
          )
        })}
      </nav>
      <div className="flex items-center gap-2 border-t border-line px-2 pt-2 text-[8px] text-slate-500">
        <Gamepad2 className="h-4 w-4 shrink-0 text-slate-500" />
        by The Agentic State
      </div>
    </aside>
  )
}
