import { useEffect, useRef, useState } from 'react'
import { Mic, Send } from 'lucide-react'
import Panel from './Panel.jsx'
import { postChat } from '../lib/api.js'

function Hologram({ active }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const cv = canvasRef.current
    if (!cv) return
    const ctx = cv.getContext('2d')
    let raf
    let t = 0

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
      t += active ? 0.08 : 0.035

      const cy = H * 0.44
      const ampMultiplier = active ? 2.6 : 1.0

      // Left voice lines (flowing red/coral neon harmonics)
      const leftWaves = [
        { c: 'rgba(239, 68, 68, 0.95)', f: 0.045, s: 1.8, a: 12 * ampMultiplier },
        { c: 'rgba(244, 63, 94, 0.75)', f: 0.065, s: -2.1, a: 8 * ampMultiplier },
        { c: 'rgba(245, 158, 11, 0.65)', f: 0.032, s: 1.3, a: 6 * ampMultiplier },
        { c: 'rgba(251, 113, 133, 0.5)', f: 0.085, s: -2.8, a: 4 * ampMultiplier },
      ]
      leftWaves.forEach((w) => {
        ctx.beginPath()
        ctx.strokeStyle = w.c
        ctx.shadowColor = '#ef4444'
        ctx.shadowBlur = active ? 14 : 6
        ctx.lineWidth = 1.6
        for (let x = 0; x <= W / 2 - 14; x += 2) {
          const envelope = Math.sin((x / (W / 2 - 14)) * Math.PI)
          const y = cy + Math.sin(x * w.f + t * w.s) * w.a * envelope
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        }
        ctx.stroke()
      })

      // Right voice lines (flowing cyan/turquoise neon harmonics)
      const rightWaves = [
        { c: 'rgba(34, 211, 238, 0.95)', f: 0.045, s: -1.8, a: 12 * ampMultiplier },
        { c: 'rgba(6, 182, 212, 0.75)', f: 0.065, s: 2.1, a: 8 * ampMultiplier },
        { c: 'rgba(59, 130, 246, 0.65)', f: 0.032, s: -1.3, a: 6 * ampMultiplier },
        { c: 'rgba(103, 232, 249, 0.5)', f: 0.085, s: 2.8, a: 4 * ampMultiplier },
      ]
      rightWaves.forEach((w) => {
        ctx.beginPath()
        ctx.strokeStyle = w.c
        ctx.shadowColor = '#06b6d4'
        ctx.shadowBlur = active ? 14 : 6
        ctx.lineWidth = 1.6
        for (let x = W / 2 + 14; x <= W; x += 2) {
          const envelope = Math.sin(((W - x) / (W / 2 - 14)) * Math.PI)
          const y = cy + Math.sin(x * w.f + t * w.s) * w.a * envelope
          x === W / 2 + 14 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        }
        ctx.stroke()
      })

      // Center eye waveform pulse when voice is active
      if (active) {
        ctx.beginPath()
        ctx.strokeStyle = 'rgba(103, 232, 249, 0.85)'
        ctx.shadowColor = '#22d3ee'
        ctx.shadowBlur = 12
        ctx.lineWidth = 2
        const pulse = Math.sin(t * 8) * 4
        ctx.moveTo(W / 2 - 14, cy + pulse)
        ctx.lineTo(W / 2 - 6, cy - pulse * 1.5)
        ctx.lineTo(W / 2, cy + pulse * 2)
        ctx.lineTo(W / 2 + 6, cy - pulse * 1.5)
        ctx.lineTo(W / 2 + 14, cy + pulse)
        ctx.stroke()
      }

      ctx.shadowBlur = 0
      raf = requestAnimationFrame(draw)
    }

    draw()
    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [active])

  return (
    <div className="relative h-[92px] w-full overflow-hidden rounded border border-line bg-[#080d1a]">
      <img
        src="/coach_avatar.png"
        alt="Live AI Coach Avatar"
        className="absolute inset-0 h-full w-full object-cover"
      />
      <canvas
        ref={canvasRef}
        className="pointer-events-none absolute inset-0 h-full w-full mix-blend-screen"
      />
    </div>
  )
}

export default function CoachPanel({ session, onCoachAdvise }) {
  const [messages, setMessages] = useState([])
  const [text, setText] = useState('')
  const speechSupported = typeof window !== 'undefined' && 'speechSynthesis' in window
  const [voiceEnabled, setVoiceEnabled] = useState(true)
  const [speaking, setSpeaking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [listening, setListening] = useState(false)
  const boxRef = useRef(null)
  const recognitionRef = useRef(null)

  const defaultCoach = session.coach_reasoning ||
    'Your downward pull on the AK47 was too slow in the first 5 frames. High upward drift detected. Try dropping your Hipfire to 72 and actively pull down earlier in the burst. Let\'s calibrate!'

  const lastCoach =
    [...messages].reverse().find((m) => m.role === 'coach')?.text ?? defaultCoach

  const speakText = (content) => {
    if (!speechSupported || !content) return
    const utterance = new SpeechSynthesisUtterance(content)
    const voices = window.speechSynthesis.getVoices()
    const naturalVoice = voices.find(
      (voice) =>
        /^en-US/i.test(voice.lang) &&
        /(natural|aria|jenny|zira|samantha|google us english|christopher)/i.test(voice.name),
    )
    const englishVoice =
      naturalVoice || voices.find((voice) => /^en-US/i.test(voice.lang)) ||
      voices.find((voice) => /^en/i.test(voice.lang))

    if (englishVoice) {
      utterance.voice = englishVoice
      utterance.lang = englishVoice.lang
    } else {
      utterance.lang = navigator.language || 'en-US'
    }
    utterance.rate = 0.94
    utterance.pitch = 1.02

    utterance.onstart = () => setSpeaking(true)
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)

    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
  }

  useEffect(() => {
    const SpeechRec = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
    if (SpeechRec) {
      const rec = new SpeechRec()
      rec.continuous = false
      rec.interimResults = false
      rec.lang = navigator.language || 'en-US'

      rec.onstart = () => setListening(true)
      rec.onend = () => setListening(false)
      rec.onerror = () => setListening(false)
      rec.onresult = (event) => {
        const spoken = event.results[0][0].transcript
        if (spoken) {
          executeChat(spoken)
        }
      }
      recognitionRef.current = rec
    }
  }, [])

  useEffect(
    () => () => {
      if (speechSupported) window.speechSynthesis.cancel()
    },
    [speechSupported],
  )

  const toggleMic = () => {
    if (recognitionRef.current) {
      if (listening) {
        recognitionRef.current.stop()
      } else {
        try {
          recognitionRef.current.start()
        } catch {
          // ignore already started
        }
      }
    } else {
      // Toggle voice output fallback
      setVoiceEnabled((v) => !v)
    }
  }

  useEffect(() => {
    boxRef.current?.scrollTo({ top: boxRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  const executeChat = async (userMsg) => {
    if (!userMsg || busy) return
    setText('')
    const history = messages.map((m) => ({ role: m.role === 'coach' ? 'assistant' : 'user', content: m.text }))
    setMessages((m) => [...m, { role: 'user', text: userMsg }])
    setBusy(true)
    try {
      const r = await postChat(userMsg, history)
      setMessages((m) => [...m, { role: 'coach', text: r.reply, verified: r.is_rag_verified }])
      if (voiceEnabled) speakText(r.reply)
      if (onCoachAdvise) {
        onCoachAdvise(r.reply, r.latest_session)
      }
    } catch (error) {
      setMessages((m) => [
        ...m,
        {
          role: 'coach',
          text: `Coach request failed: ${error.message || 'backend is not reachable'}. Check that the backend is running and try again.`,
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  const send = () => {
    const msg = text.trim()
    executeChat(msg)
  }

  return (
    <Panel
      title="Live AI Coach (Neural Voice Active)"
      id="D"
      icon={<Mic className="h-4 w-4 text-gold" />}
      className="h-full"
      bodyClass="flex flex-col justify-between gap-1.5 p-2"
    >
      <Hologram active={busy || listening || speaking} />

      <div
        ref={boxRef}
        className="min-h-0 flex-1 space-y-2 overflow-y-auto rounded border border-line bg-bg/60 p-2.5 text-[10px] leading-relaxed text-slate-200"
      >
        {messages.length === 0 ? (
          <p>
            <span className="font-semibold">Coach:</span> “{lastCoach}”
          </p>
        ) : (
          messages.map((m, i) => (
            <p key={i} className={m.role === 'user' ? 'text-right text-cyan' : ''}>
              <span className="font-semibold">{m.role === 'user' ? 'You' : 'Coach'}:</span>{' '}
              {m.role === 'coach' ? `“${m.text}”` : m.text}
              {m.verified && <span className="ml-1 text-[7px] text-safe">● RAG verified</span>}
            </p>
          ))
        )}
        {busy && <p className="blink text-slate-400">Coach is thinking…</p>}
      </div>

      <div className="flex items-center gap-1 rounded-lg border border-red-500/50 bg-bg/80 p-1">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask your Coach..."
          className="min-w-0 flex-1 bg-transparent px-1.5 text-[9.5px] text-slate-100 placeholder:text-slate-500 focus:outline-none"
        />
        <button
          onClick={toggleMic}
          title={listening ? 'Microphone active — listening...' : 'Click to speak to your Coach'}
          aria-label="Toggle coach microphone"
          className={`flex items-center gap-1 rounded border px-2 py-0.5 font-mono text-[9px] font-bold transition ${
            listening
              ? 'border-red-400 bg-red-600/30 text-white animate-pulse'
              : 'border-red-500/60 bg-red-950/30 text-red-400 hover:bg-red-900/40'
          }`}
        >
          <Mic className={`h-3 w-3 ${listening ? 'text-white' : 'text-red-400'}`} />
          {listening ? '[LISTENING...]' : '[MIC ON]'}
        </button>
        <button
          onClick={send}
          disabled={busy || !text.trim()}
          className="grid h-7 w-7 place-items-center rounded border border-red-500/40 bg-white/5 text-slate-300 transition hover:bg-rose/20 hover:text-white disabled:opacity-40"
          aria-label="Send"
        >
          <Send className="h-3.5 w-3.5" />
        </button>
      </div>
    </Panel>
  )
}
