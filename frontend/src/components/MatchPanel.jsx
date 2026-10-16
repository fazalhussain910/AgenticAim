import { Crosshair, LoaderCircle, Play } from 'lucide-react'
import Panel from './Panel.jsx'

const TAGS = ['Motion deltiaze', 'Compriex', 'Flickis Flick Path']

function LevelMeter() {
  const ticks = ['1.5', '0.5', '0.0', '0.3', '0.5', '0.6', '0.0', '0.0']
  return (
    <div className="flex h-[60px] items-stretch gap-1.5 pl-1 shrink-0">
      <div className="relative flex flex-col justify-between border-l border-t border-b border-slate-600/70 py-0.5 pl-1 pr-0.5 font-mono text-[6px] leading-none text-slate-400">
        <span className="absolute -right-1 top-0 h-[1px] w-1 bg-slate-600/70" />
        <span className="absolute -right-1 bottom-0 h-[1px] w-1 bg-slate-600/70" />
        {ticks.map((t, idx) => (
          <span key={idx}>{t}</span>
        ))}
      </div>
      <div className="relative w-[5px] overflow-hidden rounded-full bg-[#1a2133] border border-line">
        <div
          className="absolute inset-x-0 bottom-0 rounded-full"
          style={{
            height: '80%',
            background: 'linear-gradient(0deg, #22c55e 0%, #eab308 65%, #ef4444 100%)',
          }}
        />
      </div>
    </div>
  )
}

function FlickScene() {
  return (
    <div className="relative h-full min-h-[92px] w-full overflow-hidden rounded border border-line bg-black">
      <img
        src="/crosshair_capture.png"
        alt="Crosshair Capture & Flick Path"
        className="h-full w-full object-cover"
      />
    </div>
  )
}

export default function MatchPanel({ session, onAnalyze, analyzing }) {
  const { vision_analysis: v } = session
  return (
    <Panel
      title={`Latest Match Telemetry (${session.game.toUpperCase()})`}
      id="B"
      icon={<Crosshair className="h-4 w-4 text-rose" />}
      action={
        <button
          type="button"
          onClick={onAnalyze}
          disabled={analyzing}
          aria-label={analyzing ? 'Analysis running' : 'Run new analysis'}
          title={analyzing ? 'Analysis running' : 'Run new analysis'}
          className="ml-auto grid h-5 w-5 place-items-center rounded text-rose transition hover:bg-rose/15 disabled:opacity-50"
        >
          {analyzing ? <LoaderCircle className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
        </button>
      }
    >
      <div className="grid h-full min-w-0 grid-cols-[1.1fr_1fr]">
        <div className="flex min-w-0 flex-col justify-between gap-1.5 p-2.5 sm:p-3">
          <div className="space-y-1 text-[9.5px] leading-snug text-slate-200">
            <div>
              Simulated gunfight breakdown:{' '}
              {session.duration_s == null ? 'duration not recorded' : `${session.duration_s}s`}
            </div>
            <div>
              Weapon: <span className="font-semibold">{session.weapon}</span>
            </div>
            <div>
              Issues: <span className="font-semibold">{v.issues}</span>
            </div>
          </div>
          <div className="flex items-end justify-between gap-1.5 pt-1">
            <div className="flex flex-wrap gap-1.5">
              {TAGS.map((t) => (
                <span key={t} className="pill">
                  {t}
                </span>
              ))}
            </div>
            <LevelMeter />
          </div>
        </div>
        <div className="flex min-w-0 flex-col gap-1.5 border-l border-line p-2.5 sm:p-3">
          <div className="font-head text-[9.5px] font-semibold tracking-wide text-slate-200">
            Crosshair Capture &amp; Flick Path
          </div>
          <div className="min-h-0 flex-1">
            <FlickScene />
          </div>
        </div>
      </div>
    </Panel>
  )
}
