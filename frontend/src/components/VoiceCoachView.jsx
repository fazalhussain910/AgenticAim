import { useState, useRef, useEffect } from 'react'
import { Mic, MicOff, Volume2, Sparkles, Send, Radio, ShieldAlert, Award } from 'lucide-react'
import Panel from './Panel.jsx'
import { postChat, postVoiceListen, postVoiceTts } from '../lib/api.js'

export default function VoiceCoachView({ session, onCoachAdvise }) {
  const [listening, setListening] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [text, setText] = useState('')
  const [selectedVoice, setSelectedVoice] = useState('en-US-AriaNeural')
  const [messages, setMessages] = useState([
    {
      role: 'coach',
      text: 'Hey! I am your esports aim coach. Speak into your mic or type anytime. Your sliders and gunfight recoil are monitored in real time.',
    },
  ])
  const logRef = useRef(null)

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  const speak = async (msgText) => {
    if (!msgText) return
    try {
      setSpeaking(true)
      const res = await postVoiceTts(msgText, selectedVoice)
      if (res?.status === 'success' && res.audio_data) {
        const audio = new Audio(res.audio_data)
        audio.onended = () => setSpeaking(false)
        audio.onerror = () => setSpeaking(false)
        await audio.play()
        return
      }
    } catch {
      // Fallback to browser SpeechSynthesis
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        const ut = new SpeechSynthesisUtterance(msgText)
        const voices = window.speechSynthesis.getVoices()
        const female = voices.find((v) => /(aria|jenny|zira|samantha|female)/i.test(v.name))
        if (female) ut.voice = female
        ut.pitch = 1.08
        ut.rate = 1.0
        ut.onend = () => setSpeaking(false)
        window.speechSynthesis.speak(ut)
        return
      }
    }
    setSpeaking(false)
  }

  const handleSend = async (userInput) => {
    const query = userInput || text.trim()
    if (!query || busy) return
    setText('')
    const history = messages.map((m) => ({ role: m.role === 'coach' ? 'assistant' : 'user', content: m.text }))
    setMessages((prev) => [...prev, { role: 'user', text: query }])
    setBusy(true)

    try {
      const res = await postChat(query, history)
      setMessages((prev) => [...prev, { role: 'coach', text: res.reply, verified: res.is_rag_verified }])
      speak(res.reply)
      if (onCoachAdvise) onCoachAdvise(res.reply, res.latest_session)
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'coach', text: `Coach network issue: ${err.message}. Retrying...` },
      ])
    } finally {
      setBusy(false)
    }
  }

  const toggleMic = async () => {
    if (listening) {
      setListening(false)
      return
    }

    setListening(true)
    try {
      const res = await postVoiceListen()
      if (res?.status === 'success' && res.transcript) {
        handleSend(res.transcript)
      } else if (res?.message) {
        setMessages((m) => [...m, { role: 'coach', text: `🎙️ ${res.message}` }])
      }
    } catch {
      setMessages((m) => [...m, { role: 'coach', text: '🎙️ Mic active: Speak into your headset microphone.' }])
    } finally {
      setListening(false)
    }
  }

  const testFemaleVoice = () => {
    speak("Hello! I am your esports aim coach. My female neural voice is active and crystal clear. Ready for your next match!")
  }

  const QUICK_PROMPTS = [
    'Recommend my Blood Strike sensitivity settings',
    'How do I fix under-flicking on hipfire?',
    'Is my PC safe to play ranked right now?',
    'Explain the AK-47 recoil pull-down technique',
  ]

  return (
    <div className="flex h-full w-full flex-col gap-3">
      {/* Top Banner */}
      <div className="flex flex-wrap items-center justify-between rounded-lg border border-red-500/30 bg-bg2/80 p-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg border border-red-500/50 bg-red-950/40 text-red-400">
            <Radio className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <h1 className="font-head text-base font-bold text-white tracking-wide">
              Neural Voice AI Coach Station
            </h1>
            <p className="text-[10px] text-slate-400">
              Hands-free voice comms powered by Microsoft Edge Neural Female TTS & AMD Token Factory
            </p>
          </div>
        </div>

        {/* Voice Selector */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold text-slate-400">Coach Voice:</span>
          <select
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
            className="rounded border border-red-500/40 bg-bg px-2 py-1 text-[11px] font-medium text-slate-200 focus:outline-none"
          >
            <option value="en-US-AriaNeural">Female: Aria Neural (Crisp Pro - Recommended)</option>
            <option value="en-US-JennyNeural">Female: Jenny Neural (Warm & Friendly)</option>
            <option value="en-US-SaraNeural">Female: Sara Neural (Energetic)</option>
          </select>
          <button
            onClick={testFemaleVoice}
            className="flex items-center gap-1 rounded border border-cyan-500/40 bg-cyan-950/30 px-2 py-1 text-[10px] font-bold text-cyan-300 hover:bg-cyan-900/40"
          >
            <Volume2 className="h-3 w-3" />
            Test Voice
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid flex-1 grid-cols-1 gap-3 lg:grid-cols-12 min-h-0">
        {/* Left: Waveform & Mic Controls */}
        <div className="flex flex-col gap-3 lg:col-span-5 min-h-0">
          <Panel title="Live Neural Comms Visualizer" id="VC-1" className="flex-1 flex flex-col">
            <div className="flex flex-1 flex-col items-center justify-center p-6 text-center">
              {/* Pulsing Visualizer Circle */}
              <div
                className={`relative grid h-32 w-32 place-items-center rounded-full border-2 transition-all duration-300 ${
                  listening
                    ? 'border-red-400 bg-red-600/20 shadow-[0_0_35px_rgba(239,68,68,0.6)] scale-105'
                    : speaking
                    ? 'border-cyan-400 bg-cyan-600/20 shadow-[0_0_35px_rgba(6,182,212,0.6)]'
                    : 'border-line bg-bg/50'
                }`}
              >
                <Mic
                  className={`h-12 w-12 transition ${
                    listening
                      ? 'text-white animate-bounce'
                      : speaking
                      ? 'text-cyan-300 animate-pulse'
                      : 'text-slate-500'
                  }`}
                />
              </div>

              <div className="mt-4">
                <div className="font-head text-sm font-bold text-white">
                  {listening ? '🎙️ LISTENING TO YOUR HEADSET...' : speaking ? '🔊 COACH IS SPEAKING...' : 'VOICE COACH READY'}
                </div>
                <p className="mt-1 text-[10px] text-slate-400">
                  {listening
                    ? 'Speak clearly into your mic. Click button again to finish.'
                    : 'Click the button below to ask about your aim, sensitivities, or game meta.'}
                </p>
              </div>

              {/* Big Mic Button */}
              <button
                onClick={toggleMic}
                className={`mt-5 flex items-center gap-2 rounded-xl px-6 py-2.5 font-head text-xs font-bold tracking-wider shadow-lg transition ${
                  listening
                    ? 'bg-red-600 text-white shadow-red-600/50 animate-pulse'
                    : 'border border-red-500/60 bg-red-950/40 text-red-200 hover:bg-red-900/60'
                }`}
              >
                {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                {listening ? 'STOP LISTENING' : 'START TALKING (MIC ON)'}
              </button>
            </div>

            {/* Quick Prompts */}
            <div className="border-t border-line p-3">
              <div className="mb-1.5 text-[9px] font-bold text-slate-400">QUICK TACTICAL PROMPTS:</div>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_PROMPTS.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(p)}
                    className="rounded border border-white/10 bg-white/5 px-2 py-1 text-[9px] text-slate-300 transition hover:border-red-500/40 hover:bg-red-950/30 hover:text-white"
                  >
                    ⚡ {p}
                  </button>
                ))}
              </div>
            </div>
          </Panel>
        </div>

        {/* Right: Full Comms Conversation History */}
        <div className="flex flex-col gap-3 lg:col-span-7 min-h-0">
          <Panel title="Voice Comms Transcript & Coaching Logs" id="VC-2" className="flex-1 flex flex-col">
            <div
              ref={logRef}
              className="flex-1 space-y-3 overflow-y-auto p-4 text-[11px] leading-relaxed text-slate-200"
            >
              {messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg p-3 ${
                      m.role === 'user'
                        ? 'border border-cyan-500/30 bg-cyan-950/30 text-cyan-100'
                        : 'border border-red-500/30 bg-bg/90 text-slate-100'
                    }`}
                  >
                    <div className="mb-1 flex items-center gap-1.5 font-head text-[9px] font-bold tracking-wider text-slate-400">
                      {m.role === 'user' ? (
                        <span className="text-cyan-400">YOU (HEADSET MIC)</span>
                      ) : (
                        <span className="text-red-400">AI COACH (FEMALE ARIA NEURAL)</span>
                      )}
                      {m.verified && (
                        <span className="text-[8px] text-safe">● Qdrant RAG Verified</span>
                      )}
                    </div>
                    <div>{m.text}</div>
                  </div>
                </div>
              ))}
              {busy && (
                <div className="text-[10px] text-slate-400 blink">
                  Coach is analyzing gunfight telemetry & generating tactical feedback...
                </div>
              )}
            </div>

            {/* Input bar */}
            <div className="border-t border-line p-2.5">
              <div className="flex items-center gap-2 rounded-lg border border-red-500/40 bg-bg p-1.5">
                <input
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Type a message or press the Mic above..."
                  className="min-w-0 flex-1 bg-transparent px-2 text-[11px] text-white placeholder:text-slate-500 focus:outline-none"
                />
                <button
                  onClick={() => handleSend()}
                  disabled={busy || !text.trim()}
                  className="rounded bg-rose px-3 py-1 text-[10px] font-bold text-white transition hover:bg-red-600 disabled:opacity-40"
                >
                  SEND
                </button>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}
