import { useCallback, useEffect, useRef, useState } from 'react'

export const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/+$/, '')

// ---------- Fallback mock data (matches the design screenshot) ----------
export const MOCK = {
  hardware: {
    cpu_pct: 45.0,
    ram_pct: 38.0,
    ram_used_mb: 12697,
    ram_total_mb: 32768,
    gpu_pct: 62,
    gpu_desc: 'AMD Radeon GPU',
    is_safe_to_play: true,
    safety_badge: '[✅ SAFE TO PLAY]',
  },
  session: {
    game: 'Blood Strike',
    weapon: 'AK47',
    duration_s: 1,
    telemetry: { total_dx: 40, total_dy: 40, downward_pull: 15 },
    vision_analysis: {
      accuracy_score: 0.82,
      recoil_severity: 'heavy',
      flick_diagnosis: 'over-flick',
      issues: 'Heavy Over-Flick & Upward Drift',
    },
    sensitivity_sliders: {
      no_ads_sens: 72,
      iron_sight_sens: 40,
      scope_sens: 42,
      baseline: { no_ads_sens: 75, iron_sight_sens: 40, scope_sens: 40 },
    },
    coach_reasoning:
      'Your downward pull on the AK47 was too slow in the first 5 frames. High upward drift detected. Try dropping your Hipfire to 72 and actively pull down earlier in the burst. Let\'s calibrate!',
  },
  rag: {
    status: 'online',
    points: { bloodstrike_knowledge: 104, player_memory: 12 },
    total: 104,
  },
}

async function get(path) {
  const ctl = new AbortController()
  const t = setTimeout(() => ctl.abort(), 2500)
  try {
    const r = await fetch(`${API_BASE}${path}`, { signal: ctl.signal })
    if (!r.ok) throw new Error(`API request failed (${r.status} ${r.statusText})`)
    return await r.json()
  } finally {
    clearTimeout(t)
  }
}

export async function postChat(message, history) {
  const r = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  })
  if (!r.ok) throw new Error(`Chat request failed (${r.status} ${r.statusText})`)
  return r.json()
}

export async function postAnalyze() {
  const r = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ game_name: 'Blood Strike', scenario: 'recoil_not_controlled' }),
  })
  if (!r.ok) throw new Error(`Analysis request failed (${r.status} ${r.statusText})`)
  return r.json()
}

// ---------- Normalisers: tolerate partial backend responses ----------
const normHardware = (d) => ({
  ...MOCK.hardware,
  ...d,
  gpu_pct: d.gpu_pct ?? MOCK.hardware.gpu_pct,
})

const normSession = (d) => {
  const vision = d.vision_analysis || {}
  return {
    ...MOCK.session,
    ...d,
    game: d.game ?? d.game_name ?? MOCK.session.game,
    weapon: d.weapon ?? (d.game_exe ? 'Not recorded' : MOCK.session.weapon),
    duration_s: d.duration_s ?? (d.game_name ? null : MOCK.session.duration_s),
    coach_reasoning: d.newbie_advice || d.coach_reasoning || MOCK.session.coach_reasoning,
    telemetry: { ...MOCK.session.telemetry, ...(d.telemetry || {}) },
    vision_analysis: {
      ...MOCK.session.vision_analysis,
      ...vision,
      issues:
        vision.issues ||
        vision.primary_weakness ||
        (vision.recoil_severity || vision.flick_diagnosis
          ? `${vision.recoil_severity || 'No'} recoil / ${vision.flick_diagnosis || 'unknown'}`
          : MOCK.session.vision_analysis.issues),
    },
    sensitivity_sliders: {
      ...MOCK.session.sensitivity_sliders,
      ...(d.sensitivity_sliders || {}),
      baseline: MOCK.session.sensitivity_sliders.baseline,
    },
  }
}

const normRag = (d) => {
  const pts = d.points || MOCK.rag.points
  const knowledgePoints = pts.bloodstrike_knowledge ?? MOCK.rag.points.bloodstrike_knowledge
  return { ...MOCK.rag, ...d, points: pts, total: knowledgePoints }
}

/** Polls an endpoint every `ms`, falling back to mock data when offline. */
function usePoll(path, fallback, normalise, ms = 3000) {
  const [data, setData] = useState(fallback)
  const [online, setOnline] = useState(false)
  const alive = useRef(true)

  const load = useCallback(async () => {
    try {
      const d = await get(path)
      if (!alive.current) return
      setData(normalise(d))
      setOnline(true)
    } catch {
      if (!alive.current) return
      setOnline(false)
    }
  }, [path, normalise])

  useEffect(() => {
    alive.current = true
    load()
    const id = setInterval(load, ms)
    return () => {
      alive.current = false
      clearInterval(id)
    }
  }, [load, ms])

  return [data, online, load]
}

export const useHardware = () => usePoll('/api/hardware', MOCK.hardware, normHardware)
export const useSession = () => usePoll('/api/latest-session', MOCK.session, normSession)
export const useRag = () => usePoll('/api/rag/status', MOCK.rag, normRag)
