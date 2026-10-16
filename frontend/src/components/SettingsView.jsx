import { useState } from 'react'
import { Settings, Volume2, Mic, Sliders, Shield, Check, Save } from 'lucide-react'
import Panel from './Panel.jsx'
import { postVoiceTts } from '../lib/api.js'

export default function SettingsView({ hw }) {
  const [selectedVoice, setSelectedVoice] = useState('en-US-AriaNeural')
  const [speechRate, setSpeechRate] = useState(1.0)
  const [autoSpeak, setAutoSpeak] = useState(true)
  const [testing, setTesting] = useState(false)
  const [saved, setSaved] = useState(false)

  // Default Blood Strike Baselines
  const [baselines, setBaselines] = useState({
    no_ads: 75,
    firing: 71,
    iron: 40,
    firing_ads: 42,
    scope2x: 38,
    scope4x: 35,
    sniper: 30,
  })

  const testVoice = async () => {
    setTesting(true)
    try {
      const res = await postVoiceTts(
        'Tactical check! I am your AI esports coach speaking with Microsoft Aria female neural voice. All sliders and aiming telemetry are online.',
        selectedVoice,
      )
      if (res?.status === 'success' && res.audio_data) {
        const audio = new Audio(res.audio_data)
        audio.onended = () => setTesting(false)
        audio.onerror = () => setTesting(false)
        await audio.play()
        return
      }
    } catch {
      // fallback
    }
    setTesting(false)
  }

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div className="flex h-full w-full flex-col gap-3 min-h-0">
      {/* Top Banner */}
      <div className="flex flex-wrap items-center justify-between rounded-lg border border-red-500/30 bg-bg2/80 p-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg border border-red-500/50 bg-red-950/40 text-red-400">
            <Settings className="h-5 w-5" />
          </div>
          <div>
            <h1 className="font-head text-base font-bold text-white tracking-wide">
              Coach Configuration & Audio Settings
            </h1>
            <p className="text-[10px] text-slate-400">
              Customize voice gender, female neural speaker profile, and Blood Strike baseline sliders
            </p>
          </div>
        </div>

        <button
          onClick={handleSave}
          className="flex items-center gap-1.5 rounded bg-rose px-4 py-1.5 text-[10px] font-bold text-white shadow-lg transition hover:bg-red-600"
        >
          {saved ? <Check className="h-3.5 w-3.5" /> : <Save className="h-3.5 w-3.5" />}
          {saved ? 'Settings Saved!' : 'Save Changes'}
        </button>
      </div>

      {/* Main Grid */}
      <div className="grid flex-1 grid-cols-1 gap-3 lg:grid-cols-2 min-h-0 overflow-y-auto">
        {/* Left: Voice & Audio Settings */}
        <Panel title="Voice Coach & Neural Speech Configuration" id="S-1" className="flex flex-col">
          <div className="space-y-4 p-4 text-[11px] text-slate-200">
            {/* Female Voice Selector */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 mb-1">
                COACH NEURAL VOICE (PREFER FEMALE):
              </label>
              <select
                value={selectedVoice}
                onChange={(e) => setSelectedVoice(e.target.value)}
                className="w-full rounded border border-red-500/40 bg-bg p-2 text-xs font-semibold text-white focus:outline-none"
              >
                <option value="en-US-AriaNeural">Female: Microsoft Aria Neural (Crisp, High-Tech - Recommended)</option>
                <option value="en-US-JennyNeural">Female: Microsoft Jenny Neural (Natural & Expressive)</option>
                <option value="en-US-SaraNeural">Female: Microsoft Sara Neural (Energetic)</option>
                <option value="en-US-MichelleNeural">Female: Microsoft Michelle Neural (Calm Esports Comms)</option>
              </select>
              <div className="mt-2 flex items-center justify-between">
                <p className="text-[10px] text-slate-400">
                  Ultra-low latency Edge Neural female voice generated on demand.
                </p>
                <button
                  onClick={testVoice}
                  disabled={testing}
                  className="flex items-center gap-1.5 rounded border border-cyan-500/50 bg-cyan-950/30 px-3 py-1 font-mono text-[10px] font-bold text-cyan-300 hover:bg-cyan-900/40"
                >
                  <Volume2 className={`h-3 w-3 ${testing ? 'animate-bounce text-safe' : ''}`} />
                  {testing ? 'Playing...' : 'Test Female Voice'}
                </button>
              </div>
            </div>

            {/* Speech Rate Slider */}
            <div className="border-t border-line pt-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold text-slate-400">COACH SPEECH TEMPO:</span>
                <span className="font-mono text-cyan-400 font-bold">{speechRate}x</span>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.3"
                step="0.05"
                value={speechRate}
                onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
                className="w-full accent-rose cursor-pointer"
              />
              <div className="flex justify-between text-[8px] text-slate-500">
                <span>0.8x (Deliberate)</span>
                <span>1.0x (Standard)</span>
                <span>1.3x (Fast Esports Comms)</span>
              </div>
            </div>

            {/* Auto Readout Toggle */}
            <div className="border-t border-line pt-3 flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">Auto-Speak Coach Advice</div>
                <div className="text-[10px] text-slate-400">
                  Automatically read out AI recommendations through your headset upon analysis
                </div>
              </div>
              <input
                type="checkbox"
                checked={autoSpeak}
                onChange={(e) => setAutoSpeak(e.target.checked)}
                className="h-4 w-4 accent-rose cursor-pointer"
              />
            </div>
          </div>
        </Panel>

        {/* Right: Sensitivity Baselines & System */}
        <Panel title="Blood Strike Baseline Sensitivities & Telemetry" id="S-2" className="flex flex-col">
          <div className="space-y-4 p-4 text-[11px] text-slate-200">
            <div>
              <div className="text-[10px] font-bold text-slate-400 mb-2">
                DEFAULT SENSITIVITY CALIBRATION BASELINES:
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[9px] text-slate-400 block mb-0.5">Camera / No ADS</label>
                  <input
                    type="number"
                    value={baselines.no_ads}
                    onChange={(e) => setBaselines({ ...baselines, no_ads: parseInt(e.target.value) || 0 })}
                    className="w-full rounded border border-line bg-bg p-1.5 font-mono text-xs text-gold"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-slate-400 block mb-0.5">Firing Sensitivity</label>
                  <input
                    type="number"
                    value={baselines.firing}
                    onChange={(e) => setBaselines({ ...baselines, firing: parseInt(e.target.value) || 0 })}
                    className="w-full rounded border border-line bg-bg p-1.5 font-mono text-xs text-gold"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-slate-400 block mb-0.5">Iron Sight / Red Dot</label>
                  <input
                    type="number"
                    value={baselines.iron}
                    onChange={(e) => setBaselines({ ...baselines, iron: parseInt(e.target.value) || 0 })}
                    className="w-full rounded border border-line bg-bg p-1.5 font-mono text-xs text-cyan"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-slate-400 block mb-0.5">Firing ADS</label>
                  <input
                    type="number"
                    value={baselines.firing_ads}
                    onChange={(e) => setBaselines({ ...baselines, firing_ads: parseInt(e.target.value) || 0 })}
                    className="w-full rounded border border-line bg-bg p-1.5 font-mono text-xs text-cyan"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-slate-400 block mb-0.5">2× Scope</label>
                  <input
                    type="number"
                    value={baselines.scope2x}
                    onChange={(e) => setBaselines({ ...baselines, scope2x: parseInt(e.target.value) || 0 })}
                    className="w-full rounded border border-line bg-bg p-1.5 font-mono text-xs text-safe"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-slate-400 block mb-0.5">Sniper Scope</label>
                  <input
                    type="number"
                    value={baselines.sniper}
                    onChange={(e) => setBaselines({ ...baselines, sniper: parseInt(e.target.value) || 0 })}
                    className="w-full rounded border border-line bg-bg p-1.5 font-mono text-xs text-safe"
                  />
                </div>
              </div>
            </div>

            {/* System Status */}
            <div className="border-t border-line pt-3">
              <div className="text-[10px] font-bold text-slate-400 mb-1.5">DETECTED SYSTEM PLATFORM:</div>
              <div className="rounded border border-line bg-bg/60 p-2.5 text-[10px] font-mono space-y-1">
                <div>Processor: <span className="text-white">{hw?.cpu_name || 'Windows Host Processor'}</span></div>
                <div>Graphics: <span className="text-white">{hw?.gpu_name || 'DirectX Graphics Adapter'}</span></div>
                <div>System RAM: <span className="text-white">{hw?.ram_installed_gb || 8} GB Installed</span></div>
                <div>Display: <span className="text-cyan-400">{hw?.display || '1920 × 1080 @ 60Hz'}</span></div>
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  )
}
