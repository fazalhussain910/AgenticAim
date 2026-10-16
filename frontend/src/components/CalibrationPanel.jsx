import { useState, useEffect } from 'react'
import { SlidersHorizontal, Sparkles, RotateCcw } from 'lucide-react'
import Panel from './Panel.jsx'

const TABS = [
  { id: 'all', label: 'All Sliders (7)' },
  { id: 'hipfire', label: 'Camera & Hipfire' },
  { id: 'ads', label: 'ADS & Recoil' },
  { id: 'scopes', label: 'Optics & Scopes' },
]

function Row({ label, from, to, onChange, indicatorPct = 50, hasDoubleThumb = false, highlight = false }) {
  const diff = to - from
  const sign = diff > 0 ? `+${diff}` : `${diff}`
  const valCls = diff < 0 ? 'text-danger font-bold' : diff > 0 ? 'text-safe font-bold' : 'text-slate-200'
  const pct = (n) => `${Math.max(0, Math.min(100, n))}%`

  return (
    <div className={`grid grid-cols-[145px_1fr_95px] items-center gap-2.5 rounded px-1.5 py-1 transition-colors ${highlight ? 'bg-amber-500/10 border border-amber-500/20' : 'hover:bg-white/5'}`}>
      <div>
        <div className="text-[10px] font-medium text-slate-100 whitespace-nowrap">{label}</div>
        <div className="relative mt-1 h-[2.5px] w-[68px] rounded-full bg-slate-800/80">
          <div className="h-full rounded-full bg-rose/90 transition-all duration-700" style={{ width: `${indicatorPct}%` }} />
          <div
            className="absolute top-1/2 h-1.5 w-1.5 -translate-y-1/2 rounded-full border border-slate-900 bg-[#e2e8f0] transition-all duration-700"
            style={{ left: `calc(${indicatorPct}% - 3px)` }}
          />
        </div>
      </div>

      <div className="relative px-2 group">
        <div className="cal-track h-[6.5px] relative">
          <div
            className="cal-fill pointer-events-none transition-all duration-700 ease-out"
            style={{ width: pct(to) }}
          />
          {hasDoubleThumb && (
            <div
              className="cal-thumb opacity-60 pointer-events-none transition-all duration-700 ease-out"
              style={{ left: pct(from) }}
              title={`Baseline: ${from}`}
            />
          )}
          <div
            className={`cal-thumb ${diff !== 0 ? 'active' : ''} pointer-events-none group-hover:scale-125 transition-all duration-700 ease-out`}
            style={{ left: pct(to) }}
          />
        </div>
        <input
          type="range"
          min="0"
          max="150"
          value={to}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 z-20 h-full w-full cursor-pointer opacity-0"
          aria-label={label}
        />
      </div>

      <div className="font-mono text-[9.5px] text-right pr-1 text-slate-100 whitespace-nowrap">
        {from} <span className="text-slate-400">→</span>{' '}
        <span className={valCls}>{to} ({sign})</span>
      </div>
    </div>
  )
}

export default function CalibrationPanel({ session, coachOverrides }) {
  const s = session?.sensitivity_sliders || {}
  const b = s.baseline || {}

  const [tab, setTab] = useState('all')
  const [justCalibrated, setJustCalibrated] = useState(false)

  // Full 7 Blood Strike sensitivity slider state
  const [values, setValues] = useState({
    camera_sens: s.camera_sens ?? s.no_ads_sens ?? 97,
    firing_sens: s.firing_sens ?? 92,
    ads_sens: s.ads_sens ?? s.iron_sight_sens ?? 55,
    firing_ads_sens: s.firing_ads_sens ?? 58,
    scope_2x: s.scope_2x ?? 48,
    scope_4x: s.scope_4x ?? 44,
    scope_sniper: s.scope_sniper ?? 40,
  })

  const [baselines, setBaselines] = useState({
    camera_sens: b.camera_sens ?? b.no_ads_sens ?? 75,
    firing_sens: b.firing_sens ?? 75,
    ads_sens: b.ads_sens ?? b.iron_sight_sens ?? 40,
    firing_ads_sens: b.firing_ads_sens ?? 40,
    scope_2x: b.scope_2x ?? 40,
    scope_4x: b.scope_4x ?? 35,
    scope_sniper: b.scope_sniper ?? 30,
  })

  // Synchronize with session updates
  useEffect(() => {
    if (s && Object.keys(s).length > 0) {
      setValues((prev) => ({
        ...prev,
        camera_sens: s.camera_sens ?? s.no_ads_sens ?? prev.camera_sens,
        firing_sens: s.firing_sens ?? (s.no_ads_sens ? Math.round(s.no_ads_sens * 0.95) : prev.firing_sens),
        ads_sens: s.ads_sens ?? s.iron_sight_sens ?? prev.ads_sens,
        firing_ads_sens: s.firing_ads_sens ?? (s.iron_sight_sens ? Math.round(s.iron_sight_sens * 1.05) : prev.firing_ads_sens),
        scope_2x: s.scope_2x ?? (s.scope_sens ? Math.round(s.scope_sens * 0.95) : prev.scope_2x),
        scope_4x: s.scope_4x ?? (s.scope_sens ? Math.round(s.scope_sens * 0.85) : prev.scope_4x),
        scope_sniper: s.scope_sniper ?? (s.scope_sens ? Math.round(s.scope_sens * 0.75) : prev.scope_sniper),
      }))
    }
  }, [s])

  // React to dynamic Coach chat recommendations (automatic slider repositioning!)
  useEffect(() => {
    if (coachOverrides && Object.keys(coachOverrides).length > 0) {
      setValues((prev) => ({
        ...prev,
        camera_sens: coachOverrides.camera_sens ?? coachOverrides.no_ads_sens ?? prev.camera_sens,
        firing_sens: coachOverrides.firing_sens ?? prev.firing_sens,
        ads_sens: coachOverrides.ads_sens ?? coachOverrides.iron_sight_sens ?? prev.ads_sens,
        firing_ads_sens: coachOverrides.firing_ads_sens ?? prev.firing_ads_sens,
        scope_2x: coachOverrides.scope_2x ?? prev.scope_2x,
        scope_4x: coachOverrides.scope_4x ?? prev.scope_4x,
        scope_sniper: coachOverrides.scope_sniper ?? prev.scope_sniper,
      }))
      setJustCalibrated(true)
      const timer = setTimeout(() => setJustCalibrated(false), 3000)
      return () => clearTimeout(timer)
    }
  }, [coachOverrides])

  const updateVal = (key, val) => {
    setValues((prev) => ({ ...prev, [key]: val }))
  }

  const resetDefaults = () => {
    setValues({ ...baselines })
  }

  // All 7 Blood Strike sensitivity slider metadata
  const SLIDERS = [
    {
      key: 'camera_sens',
      category: 'hipfire',
      label: 'Camera Sens (No Scope)',
      desc: 'Looking around & hipfire flick speed',
      indicatorPct: 75,
      hasDoubleThumb: true,
    },
    {
      key: 'firing_sens',
      category: 'hipfire',
      label: 'Firing Sens (Hipfire)',
      desc: 'Horizontal tracking while spraying hipfire',
      indicatorPct: 75,
      hasDoubleThumb: false,
    },
    {
      key: 'ads_sens',
      category: 'ads',
      label: 'ADS Sens (Red Dot/1X)',
      desc: 'Target acquisition with 1X iron sight',
      indicatorPct: 40,
      hasDoubleThumb: true,
    },
    {
      key: 'firing_ads_sens',
      category: 'ads',
      label: 'Firing ADS (Recoil)',
      desc: 'Vertical spray pull-down under weapon recoil',
      indicatorPct: 40,
      hasDoubleThumb: false,
    },
    {
      key: 'scope_2x',
      category: 'scopes',
      label: '2× Scope Sensitivity',
      desc: 'Mid-range optical tracking',
      indicatorPct: 40,
      hasDoubleThumb: true,
    },
    {
      key: 'scope_4x',
      category: 'scopes',
      label: '4× Scope Sensitivity',
      desc: 'High-power rifle magnification',
      indicatorPct: 35,
      hasDoubleThumb: false,
    },
    {
      key: 'scope_sniper',
      category: 'scopes',
      label: 'Sniper Scope Sensitivity',
      desc: 'Pinpoint precision long-range headshots',
      indicatorPct: 30,
      hasDoubleThumb: true,
    },
  ]

  const filtered = tab === 'all' ? SLIDERS : SLIDERS.filter((s) => s.category === tab)

  const primaryTarget = values.camera_sens ?? 97
  const targetPct = `${Math.max(16, Math.min(84, primaryTarget))}%`

  return (
    <Panel
      title="In-Game Slider Calibration (Blood Strike)"
      id="C"
      icon={<SlidersHorizontal className="h-4 w-4 text-slate-400" />}
      action={
        <div className="flex items-center gap-2">
          {justCalibrated && (
            <span className="flex items-center gap-1 rounded border border-amber-500/50 bg-amber-500/20 px-2 py-0.5 font-mono text-[8px] font-bold text-amber-300 animate-pulse">
              <Sparkles className="h-2.5 w-2.5" />
              COACH CALIBRATED
            </span>
          )}
          <button
            onClick={resetDefaults}
            title="Reset to Blood Strike baseline defaults"
            className="flex items-center gap-1 rounded border border-slate-700 bg-white/5 px-2 py-0.5 text-[8.5px] text-slate-300 transition hover:bg-white/10 hover:text-white"
          >
            <RotateCcw className="h-2.5 w-2.5" />
            Reset
          </button>
        </div>
      }
      bodyClass="p-2 sm:p-2.5 flex flex-col justify-between"
    >
      {/* Category Tabs */}
      <div className="flex items-center justify-between border-b border-line pb-1.5">
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded px-2 py-0.5 text-[8.5px] font-medium transition-colors ${
                tab === t.id
                  ? 'bg-rose/20 text-rose font-bold border border-rose/30'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <span className="text-[8px] text-slate-400 hidden sm:inline">
          {filtered.length} sliders active
        </span>
      </div>

      {/* Target Metric Indicator */}
      <div className="grid grid-cols-[145px_1fr_95px] items-center gap-2.5 pt-1">
        <span />
        <div className="relative h-5 px-2">
          <div
            className="absolute -translate-x-1/2 text-center text-[8.5px] text-slate-200 pointer-events-none transition-all duration-700 ease-out"
            style={{ left: targetPct }}
          >
            Target metric
            <div className="text-[8px] leading-none text-slate-300">▼</div>
          </div>
          <div
            className="absolute top-[18px] h-[75px] border-l border-dashed border-slate-500/60 pointer-events-none transition-all duration-700 ease-out"
            style={{ left: targetPct }}
          />
        </div>
        <div className="text-[8.5px] text-right pr-1 text-slate-400 font-medium">
          Change
        </div>
      </div>

      {/* Sliders List */}
      <div className="mt-1 max-h-[145px] overflow-y-auto space-y-1.5 pr-1">
        {filtered.map((item) => (
          <Row
            key={item.key}
            label={item.label}
            from={baselines[item.key] ?? 40}
            to={values[item.key] ?? 40}
            onChange={(val) => updateVal(item.key, val)}
            indicatorPct={item.indicatorPct}
            hasDoubleThumb={item.hasDoubleThumb}
            highlight={justCalibrated}
          />
        ))}
      </div>
    </Panel>
  )
}
