import { useState } from 'react'
import { Header, Sidebar } from './components/Shell.jsx'
import HardwarePanel from './components/HardwarePanel.jsx'
import TelemetryPanel from './components/TelemetryPanel.jsx'
import MatchPanel from './components/MatchPanel.jsx'
import CalibrationPanel from './components/CalibrationPanel.jsx'
import CoachPanel from './components/CoachPanel.jsx'
import RagPanel from './components/RagPanel.jsx'
import { useHardware, useSession, useRag, postAnalyze } from './lib/api.js'

export default function App() {
  const [nav, setNav] = useState('dashboard')
  const [hw, hwOnline] = useHardware()
  const [session, , reloadSession] = useSession()
  const [rag] = useRag()
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState('')

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

  return (
    <div className="flex h-full min-h-screen flex-col">
      <Header hw={hw} online={hwOnline} />
      <div className="flex min-h-0 flex-1">
        <Sidebar active={nav} onChange={setNav} />
        <main className="min-w-0 flex-1 overflow-auto p-2.5 sm:p-3.5 flex flex-col">
          <div className="dashboard-grid mx-auto grid w-full flex-1 max-w-[1600px] grid-cols-1 gap-2.5 sm:grid-cols-2 lg:ml-0 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.15fr)] lg:grid-rows-[minmax(136px,0.95fr)_minmax(168px,1.2fr)_minmax(146px,1.05fr)] lg:gap-2.5">
            <div className="min-h-0 min-w-0 lg:col-start-1 lg:row-start-1"><HardwarePanel hw={hw} /></div>
            <div className="min-h-0 min-w-0 lg:col-start-2 lg:row-start-1"><TelemetryPanel hw={hw} /></div>
            <div className="min-h-0 min-w-0 lg:col-start-3 lg:row-span-2 lg:row-start-1">
              <CoachPanel session={session} />
            </div>

            <div className="min-h-0 min-w-0 lg:col-span-2 lg:col-start-1 lg:row-start-2">
              <MatchPanel session={session} onAnalyze={analyze} analyzing={analyzing} />
            </div>

            <div className="min-h-0 min-w-0 lg:col-span-2 lg:col-start-1 lg:row-start-3"><CalibrationPanel session={session} /></div>
            <div className="min-h-0 min-w-0 lg:col-start-3 lg:row-start-3"><RagPanel rag={rag} /></div>
          </div>

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
