import { useState, useEffect } from 'react'
import { SlidersHorizontal } from 'lucide-react'
import Panel from './Panel.jsx'

function Row({ label, from, to, onChange, indicatorPct = 50, hasDoubleThumb = false }) {
  const diff = to - from
  const sign = diff > 0 ? `+${diff}` : `${diff}`
  const valCls = diff < 0 ? 'text-danger font-bold' : diff > 0 ? 'text-safe font-bold' : 'text-slate-200'
  const pct = (n) => `${Math.max(0, Math.min(100, n))}%`

  return (
    <div className="grid grid-cols-[135px_1fr_105px] items-center gap-3">
      <div>
        <div className="text-[10px] font-medium text-slate-100 whitespace-nowrap">{label}</div>
        <div className="relative mt-1.5 h-[2.5px] w-[72px] rounded-full bg-slate-800/80">
          <div className="h-full rounded-full bg-rose/90" style={{ width: `${indicatorPct}%` }} />
          <div
            className="absolute top-1/2 h-1.5 w-1.5 -translate-y-1/2 rounded-full border border-slate-900 bg-[#e2e8f0]"
            style={{ left: `calc(${indicatorPct}% - 3px)` }}
          />
        </div>
      </div>
      <div className="relative px-2 group">
        <div className="cal-track h-[6.5px] relative">
          <div className="cal-fill pointer-events-none" style={{ width: pct(to) }} />
          {hasDoubleThumb && (
            <div
              className="cal-thumb opacity-75 pointer-events-none"
              style={{ left: pct(from) }}
            />
          )}
          <div
            className={`cal-thumb ${diff !== 0 ? 'active' : ''} pointer-events-none group-hover:scale-125 transition-transform`}
            style={{ left: pct(to) }}
          />
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={to}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 z-20 h-full w-full cursor-pointer opacity-0"
          aria-label={label}
        />
      </div>
      <div className="font-mono text-[10px] text-right pr-2 text-slate-100 whitespace-nowrap">
        {from} <span className="text-slate-400">→</span>{' '}
        <span className={valCls}>{to} ({sign})</span>
      </div>
    </div>
  )
}

export default function CalibrationPanel({ session }) {
  const s = session.sensitivity_sliders || {}
  const b = s.baseline || { no_ads_sens: 75, iron_sight_sens: 40, scope_sens: 40 }

  const [noAds, setNoAds] = useState(s.no_ads_sens ?? 72)
  const [ironSight, setIronSight] = useState(s.iron_sight_sens ?? 40)
  const [scopes, setScopes] = useState(s.scope_sens ?? 42)

  useEffect(() => {
    if (s.no_ads_sens != null) setNoAds(s.no_ads_sens)
    if (s.iron_sight_sens != null) setIronSight(s.iron_sight_sens)
    if (s.scope_sens != null) setScopes(s.scope_sens)
  }, [s.no_ads_sens, s.iron_sight_sens, s.scope_sens])

  // Target percentage clamped so it stays neatly within the slider track and never collides with columns
  const rawTarget = noAds ?? 72
  const targetPct = `${Math.max(16, Math.min(84, rawTarget))}%`

  return (
    <Panel
      title="In-Game Slider Calibration"
      id="C"
      icon={<SlidersHorizontal className="h-4 w-4 text-slate-400" />}
      bodyClass="p-3 sm:p-3.5 flex flex-col justify-between"
    >
      <div className="grid grid-cols-[135px_1fr_105px] items-center gap-3">
        <span />
        <div className="relative h-6 px-2">
          <div
            className="absolute -translate-x-1/2 text-center text-[9px] text-slate-200 pointer-events-none"
            style={{ left: targetPct }}
          >
            Target metric
            <div className="text-[9px] leading-none text-slate-300">▼</div>
          </div>
          <div
            className="absolute top-[22px] h-[82px] border-l border-dashed border-slate-500/70 pointer-events-none"
            style={{ left: targetPct }}
          />
        </div>
        <div className="text-[9px] text-right pr-2 text-slate-300 whitespace-nowrap font-medium">
          Current change
        </div>
      </div>
      <div className="mt-1 space-y-3">
        <Row
          label="No ADS (Hipfire):"
          from={b.no_ads_sens}
          to={noAds}
          onChange={setNoAds}
          indicatorPct={72}
        />
        <Row
          label="Iron Sight / Holo:"
          from={b.iron_sight_sens}
          to={ironSight}
          onChange={setIronSight}
          indicatorPct={40}
        />
        <Row
          label="Scopes (2X-8X):"
          from={b.scope_sens}
          to={scopes}
          onChange={setScopes}
          indicatorPct={40}
          hasDoubleThumb={true}
        />
      </div>
    </Panel>
  )
}
