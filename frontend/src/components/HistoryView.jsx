import { useEffect, useState } from 'react'
import { History, RefreshCw, Crosshair, Cpu, Award, Zap } from 'lucide-react'
import Panel from './Panel.jsx'
import { fetchHistory } from '../lib/api.js'

export default function HistoryView() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedSession, setSelectedSession] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const data = await fetchHistory(50)
      setHistory(data || [])
      if (data && data.length > 0 && !selectedSession) {
        setSelectedSession(data[0])
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div className="flex h-full w-full flex-col gap-3 min-h-0">
      {/* Top Banner */}
      <div className="flex flex-wrap items-center justify-between rounded-lg border border-red-500/30 bg-bg2/80 p-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg border border-red-500/50 bg-red-950/40 text-red-400">
            <History className="h-5 w-5" />
          </div>
          <div>
            <h1 className="font-head text-base font-bold text-white tracking-wide">
              Match History & Gunfight Telemetry Log
            </h1>
            <p className="text-[10px] text-slate-400">
              Persistent SQLite audit log tracking every flick, recoil pull, and sensitivity calibration
            </p>
          </div>
        </div>

        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 rounded border border-red-500/40 bg-bg px-3 py-1.5 text-[10px] font-bold text-red-300 hover:bg-white/5"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          Refresh Records
        </button>
      </div>

      {/* Main Content */}
      <div className="grid flex-1 grid-cols-1 gap-3 lg:grid-cols-12 min-h-0">
        {/* Left: Table of past sessions */}
        <div className="flex flex-col lg:col-span-8 min-h-0">
          <Panel title="Logged Aim Sessions (SQLite Persistence)" id="H-1" className="flex-1 flex flex-col min-h-0">
            <div className="flex-1 overflow-auto p-2">
              <table className="w-full text-left text-[10px]">
                <thead className="sticky top-0 bg-bg2 text-[9px] uppercase tracking-wider text-slate-400 border-b border-line">
                  <tr>
                    <th className="p-2">ID</th>
                    <th className="p-2">Scenario</th>
                    <th className="p-2">Accuracy</th>
                    <th className="p-2">Recoil</th>
                    <th className="p-2">Mouse Δx / Δy</th>
                    <th className="p-2">No ADS</th>
                    <th className="p-2">Iron Sight</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/40 text-slate-200">
                  {history.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="p-4 text-center text-slate-500">
                        {loading ? 'Loading telemetry database...' : 'No aim sessions recorded yet. Run an analysis on the dashboard!'}
                      </td>
                    </tr>
                  ) : (
                    history.map((s) => {
                      const isSel = selectedSession?.id === s.id
                      const t = s.telemetry || {}
                      const v = s.vision_analysis || {}
                      const sens = s.sensitivity_sliders || {}
                      return (
                        <tr
                          key={s.id}
                          onClick={() => setSelectedSession(s)}
                          className={`cursor-pointer transition hover:bg-white/5 ${
                            isSel ? 'bg-red-950/40 font-semibold text-white' : ''
                          }`}
                        >
                          <td className="p-2 font-mono text-cyan-400">#{s.id}</td>
                          <td className="p-2 capitalize">{s.scenario?.replace(/_/g, ' ') || 'Aim Test'}</td>
                          <td className="p-2 font-mono text-safe">
                            {typeof v.accuracy_score === 'number' ? `${Math.round(v.accuracy_score * 100)}%` : '85%'}
                          </td>
                          <td className="p-2">
                            <span
                              className={`rounded px-1.5 py-0.5 text-[8.5px] font-bold ${
                                v.recoil_detected
                                  ? 'bg-danger/20 text-danger border border-danger/40'
                                  : 'bg-safe/20 text-safe border border-safe/40'
                              }`}
                            >
                              {v.recoil_severity || (v.recoil_detected ? 'detected' : 'none')}
                            </span>
                          </td>
                          <td className="p-2 font-mono text-slate-300">
                            {t.total_dx ?? 0}px / {t.total_dy ?? 0}px
                          </td>
                          <td className="p-2 font-mono text-gold font-bold">
                            {sens.no_ads_sens ?? 75}
                          </td>
                          <td className="p-2 font-mono text-cyan-300 font-bold">
                            {sens.iron_sight_sens ?? 40}
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        {/* Right: Selected Session Deep Dive */}
        <div className="flex flex-col lg:col-span-4 min-h-0">
          <Panel title="Session Analysis & Reasoning" id="H-2" className="flex-1 flex flex-col min-h-0">
            {selectedSession ? (
              <div className="flex flex-1 flex-col justify-between overflow-y-auto p-3 text-[11px] leading-relaxed text-slate-200">
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-line pb-2">
                    <span className="font-head text-xs font-bold text-white">
                      SESSION #{selectedSession.id}
                    </span>
                    <span className="text-[9px] text-slate-400">
                      Game: {selectedSession.game_name || 'Blood Strike'}
                    </span>
                  </div>

                  {/* Sliders Snapshot */}
                  <div className="rounded border border-line bg-bg/60 p-2">
                    <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                      CALIBRATED SENSITIVITY PROFILE:
                    </div>
                    <div className="grid grid-cols-2 gap-1.5 text-[10px] font-mono">
                      <div>Camera / No ADS: <span className="text-gold font-bold">{selectedSession.sensitivity_sliders?.no_ads_sens || 75}</span></div>
                      <div>Firing Sens: <span className="text-gold font-bold">{selectedSession.sensitivity_sliders?.firing_sens || 71}</span></div>
                      <div>Iron Sight / ADS: <span className="text-cyan font-bold">{selectedSession.sensitivity_sliders?.iron_sight_sens || 40}</span></div>
                      <div>Firing ADS: <span className="text-cyan font-bold">{selectedSession.sensitivity_sliders?.firing_ads_sens || 42}</span></div>
                      <div>2× Scope: <span className="text-safe font-bold">{selectedSession.sensitivity_sliders?.scope_2x || 38}</span></div>
                      <div>Sniper Scope: <span className="text-safe font-bold">{selectedSession.sensitivity_sliders?.scope_sniper || 30}</span></div>
                    </div>
                  </div>

                  {/* Telemetry Breakdown */}
                  <div className="rounded border border-line bg-bg/60 p-2">
                    <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                      HARDWARE TELEMETRY DELTAS:
                    </div>
                    <div className="text-[10px] space-y-1 text-slate-300">
                      <div>Horizontal Movement: <span className="font-mono text-white">{selectedSession.telemetry?.total_dx || 0}px</span></div>
                      <div>Vertical Recoil Pull: <span className="font-mono text-white">{selectedSession.telemetry?.downward_pull || 0}px</span></div>
                      <div>Flick Classification: <span className="font-mono text-cyan-300">{selectedSession.vision_analysis?.flick_diagnosis || 'normal'}</span></div>
                    </div>
                  </div>

                  {/* Coach Reasoning */}
                  <div className="rounded border border-red-500/30 bg-red-950/20 p-2.5 text-slate-100">
                    <div className="mb-1 text-[9px] font-bold text-red-400">AI COACH REASONING:</div>
                    <p className="text-[10px] leading-relaxed italic">
                      “{selectedSession.coach_reasoning || 'Session telemetry logged cleanly into persistent database.'}”
                    </p>
                  </div>
                </div>

                <div className="mt-3 text-[9px] text-slate-500 text-right">
                  Logged into SQLite database • agenticaim.db
                </div>
              </div>
            ) : (
              <div className="flex flex-1 items-center justify-center p-6 text-center text-[11px] text-slate-500">
                Select a session row from the table to view its full telemetry inspection.
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  )
}
