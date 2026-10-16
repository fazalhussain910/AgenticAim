import { useState } from 'react'
import { Header, Sidebar } from './components/Shell.jsx'
import HardwarePanel from './components/HardwarePanel.jsx'
import TelemetryPanel from './components/TelemetryPanel.jsx'
import MatchPanel from './components/MatchPanel.jsx'
import CalibrationPanel from './components/CalibrationPanel.jsx'
import CoachPanel from './components/CoachPanel.jsx'
import RagPanel from './components/RagPanel.jsx'
import VoiceCoachView from './components/VoiceCoachView.jsx'
import HistoryView from './components/HistoryView.jsx'
import QdrantView from './components/QdrantView.jsx'
import SettingsView from './components/SettingsView.jsx'
import { useHardware, useSession, useRag, postAnalyze } from './lib/api.js'

function parseSensFromText(text) {
  const updates = {}
  if (!text) return updates

  // Camera / No ADS
  const noAdsMatch = text.match(/(?:Camera Sensitivity|No ADS(?:\s*Steering)?|hipfire)[^\d]*(\d{2,3})/i)
  if (noAdsMatch) updates.camera_sens = parseInt(noAdsMatch[1], 10)

  // Firing sens
  const firingMatch = text.match(/(?:Firing Sensitivity)[^\d]*(\d{2,3})/i)
  if (firingMatch) updates.firing_sens = parseInt(firingMatch[1], 10)

  // ADS / Iron Sight / Red Dot
  const adsMatch = text.match(/(?:ADS Sensitivity|Iron Sight|Red Dot)[^\d]*(\d{2,3})/i)
  if (adsMatch) updates.ads_sens = parseInt(adsMatch[1], 10)

  // Firing ADS
  const firingAdsMatch = text.match(/(?:Firing ADS(?:\s*Sensitivity)?)[^\d]*(\d{2,3})/i)
  if (firingAdsMatch) updates.firing_ads_sens = parseInt(firingAdsMatch[1], 10)

  // Scope 2X
  const scope2xMatch = text.match(/(?:2[x×]\s*Scope)[^\d]*(\d{2,3})/i)
  if (scope2xMatch) updates.scope_2x = parseInt(scope2xMatch[1], 10)

  // Scope 4X
  const scope4xMatch = text.match(/(?:4[x×]\s*Scope)[^\d]*(\d{2,3})/i)
  if (scope4xMatch) updates.scope_4x = parseInt(scope4xMatch[1], 10)

  // Sniper Scope
  const sniperMatch = text.match(/(?:Sniper(?:\s*Scope)?)[^\d]*(\d{2,3})/i)
  if (sniperMatch) updates.scope_sniper = parseInt(sniperMatch[1], 10)

  // General Scope
  const generalScopeMatch = text.match(/(?:Scope Sensitivity|Scopes?)[^\d]*(\d{2,3})/i)
  if (generalScopeMatch && !updates.scope_2x) {
    const v = parseInt(generalScopeMatch[1], 10)
    updates.scope_sens = v
    updates.scope_2x = Math.round(v * 0.95)
    updates.scope_4x = Math.round(v * 0.85)
    updates.scope_sniper = Math.round(v * 0.75)
  }

  return updates
}

export default function App() {
  const [nav, setNav] = useState('dashboard')
  const [hw, hwOnline] = useHardware()
  const [session, , reloadSession] = useSession()
  const [rag] = useRag()
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState('')
  const [coachOverrides, setCoachOverrides] = useState(null)

  const analyze = async () => {
    setAnalyzing(true)
    setAnalysisError('')
    try {
      await postAnalyze()
      await reloadSession()
    } catch (error) {
      setAnalysisError(error.message || 'Unable to run analysis.')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleCoachAdvise = (replyText, latestSession) => {
    // 1. Extract values from latest_session if available
    let extracted = {}
    if (latestSession?.sensitivity_sliders) {
      extracted = { ...latestSession.sensitivity_sliders }
    }
    // 2. Extract specific numbers from reply text
    const textExtracted = parseSensFromText(replyText)
    const combined = { ...extracted, ...textExtracted }

    if (Object.keys(combined).length > 0) {
      setCoachOverrides((prev) => ({ ...(prev || {}), ...combined }))
    }
  }

  return (
    <div className="flex h-full min-h-screen flex-col">
      <Header hw={hw} online={hwOnline} />
      <div className="flex min-h-0 flex-1">
        <Sidebar active={nav} onChange={setNav} />
        <main className="min-w-0 flex-1 overflow-auto p-2.5 sm:p-3.5 flex flex-col">
          {nav === 'dashboard' && (
            <div className="dashboard-grid mx-auto grid w-full flex-1 max-w-[1600px] grid-cols-1 gap-2.5 sm:grid-cols-2 lg:ml-0 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.15fr)] lg:grid-rows-[minmax(136px,0.95fr)_minmax(168px,1.2fr)_minmax(146px,1.05fr)] lg:gap-2.5">
              <div className="min-h-0 min-w-0 lg:col-start-1 lg:row-start-1"><HardwarePanel hw={hw} /></div>
              <div className="min-h-0 min-w-0 lg:col-start-2 lg:row-start-1"><TelemetryPanel hw={hw} /></div>
              <div className="min-h-0 min-w-0 lg:col-start-3 lg:row-span-2 lg:row-start-1">
                <CoachPanel session={session} onCoachAdvise={handleCoachAdvise} />
              </div>

              <div className="min-h-0 min-w-0 lg:col-span-2 lg:col-start-1 lg:row-start-2">
                <MatchPanel session={session} onAnalyze={analyze} analyzing={analyzing} />
              </div>

              <div className="min-h-0 min-w-0 lg:col-span-2 lg:col-start-1 lg:row-start-3">
                <CalibrationPanel session={session} coachOverrides={coachOverrides} />
              </div>
              <div className="min-h-0 min-w-0 lg:col-start-3 lg:row-start-3"><RagPanel rag={rag} /></div>
            </div>
          )}

          {nav === 'voice' && (
            <div className="mx-auto flex-1 w-full max-w-[1600px]">
              <VoiceCoachView session={session} onCoachAdvise={handleCoachAdvise} />
            </div>
          )}

          {nav === 'history' && (
            <div className="mx-auto flex-1 w-full max-w-[1600px]">
              <HistoryView />
            </div>
          )}

          {nav === 'qdrant' && (
            <div className="mx-auto flex-1 w-full max-w-[1600px]">
              <QdrantView rag={rag} />
            </div>
          )}

          {nav === 'settings' && (
            <div className="mx-auto flex-1 w-full max-w-[1600px]">
              <SettingsView hw={hw} />
            </div>
          )}

          {analysisError && (
            <p role="alert" className="mt-2 text-right text-[9px] text-red-300">
              Analysis failed: {analysisError}
            </p>
          )}
        </main>
      </div>
    </div>
  )
}
