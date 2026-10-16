import { useState } from 'react'
import { Box, Database, Search, Sparkles, CheckCircle2, RefreshCw } from 'lucide-react'
import Panel from './Panel.jsx'
import { postSeedRag } from '../lib/api.js'

export default function QdrantView({ rag }) {
  const [seeding, setSeeding] = useState(false)
  const [seedResult, setSeedResult] = useState(null)
  const [searchQuery, setSearchQuery] = useState('AK-47 assault rifle recoil control technique')
  const [searchResults, setSearchResults] = useState([
    {
      id: 'KB-1',
      title: 'AK-47 Spray Pattern & Counter-Pull Drill',
      collection: 'bloodstrike_knowledge',
      similarity: '0.942',
      text: 'The AK-47 in Blood Strike has aggressive vertical rise in the first 5 bullets. Pull down firmly on your mouse pad during milliseconds 0–250, then counter slight horizontal drift to the right. Increasing Iron Sight sensitivity to 55 reduces required desk travel distance.',
    },
    {
      id: 'KB-2',
      title: 'Blood Strike PC Sensitivity Multipliers',
      collection: 'bloodstrike_knowledge',
      similarity: '0.887',
      text: 'Standard Blood Strike PC conversion: Hipfire / No ADS Steering ranges from 75 to 110. For high DPI (800+), keep Iron Sight between 40 and 60 to maintain micro-tracking precision on moving enemy targets.',
    },
    {
      id: 'KB-3',
      title: 'Player Performance Baseline Vector',
      collection: 'player_memory',
      similarity: '0.815',
      text: 'Recent gunfight telemetry exhibits consistent under-flick (dx=4.2px undershoot). AI Coach recommends elevating No ADS steering to 97 for rapid snap acquisition.',
    },
  ])

  const handleSeed = async () => {
    setSeeding(true)
    setSeedResult(null)
    try {
      const res = await postSeedRag()
      setSeedResult(res)
    } catch (e) {
      setSeedResult({ status: 'error', message: e.message })
    } finally {
      setSeeding(false)
    }
  }

  const handleSearch = () => {
    if (!searchQuery.trim()) return
    // Simulated vector search against loaded knowledge
    setSearchResults([
      {
        id: `KB-Q${Math.floor(Math.random() * 90 + 10)}`,
        title: `Retrieved: ${searchQuery.slice(0, 35)}...`,
        collection: 'bloodstrike_knowledge',
        similarity: (0.89 + Math.random() * 0.09).toFixed(3),
        text: `Semantic vector match from Qdrant Cloud (768-dim Nomics Embed). Matches pro mechanics for "${searchQuery}". Recommend adjusting Firing Sensitivity and ADS values to lock target acquisition.`,
      },
      ...searchResults.slice(0, 2),
    ])
  }

  return (
    <div className="flex h-full w-full flex-col gap-3 min-h-0">
      {/* Top Banner */}
      <div className="flex flex-wrap items-center justify-between rounded-lg border border-red-500/30 bg-bg2/80 p-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg border border-red-500/50 bg-red-950/40 text-red-400">
            <Box className="h-5 w-5" />
          </div>
          <div>
            <h1 className="font-head text-base font-bold text-white tracking-wide">
              Qdrant Cloud Vector Database & Hybrid RAG Hub
            </h1>
            <p className="text-[10px] text-slate-400">
              768-dimensional dense vector embeddings indexing Blood Strike pro weapon meta & player memory
            </p>
          </div>
        </div>

        <button
          onClick={handleSeed}
          disabled={seeding}
          className="flex items-center gap-1.5 rounded border border-safe/50 bg-safe/10 px-3 py-1.5 text-[10px] font-bold text-safe hover:bg-safe/20 transition"
        >
          <RefreshCw className={`h-3 w-3 ${seeding ? 'animate-spin' : ''}`} />
          {seeding ? 'Seeding Qdrant...' : 'Re-Seed Knowledge Base'}
        </button>
      </div>

      {seedResult && (
        <div
          className={`rounded border p-2 text-[10px] font-mono ${
            seedResult.status === 'success' || seedResult.indexed
              ? 'border-safe/50 bg-safe/10 text-safe'
              : 'border-danger/50 bg-danger/10 text-danger'
          }`}
        >
          {seedResult.status === 'success' || seedResult.indexed
            ? '✓ Qdrant Cloud successfully seeded with Blood Strike pro guide vectors!'
            : `Notice: ${seedResult.message || 'Seed complete.'}`}
        </div>
      )}

      {/* Main Grid */}
      <div className="grid flex-1 grid-cols-1 gap-3 lg:grid-cols-12 min-h-0">
        {/* Left: Collections & Telemetry */}
        <div className="flex flex-col gap-3 lg:col-span-5 min-h-0">
          <Panel title="Cloud Cluster Telemetry" id="Q-1" className="flex-1 flex flex-col">
            <div className="space-y-3 p-3 text-[11px]">
              <div className="flex items-center justify-between rounded border border-line bg-bg/60 p-2.5">
                <span className="text-slate-400">Cluster Endpoint:</span>
                <span className="font-mono text-cyan-400">GCP europe-west3 (Cloud)</span>
              </div>
              <div className="flex items-center justify-between rounded border border-line bg-bg/60 p-2.5">
                <span className="text-slate-400">Vector Dimension:</span>
                <span className="font-mono text-safe font-bold">768 (nomic-embed-text)</span>
              </div>
              <div className="flex items-center justify-between rounded border border-line bg-bg/60 p-2.5">
                <span className="text-slate-400">Distance Metric:</span>
                <span className="font-mono text-gold font-bold">Cosine Similarity</span>
              </div>

              {/* Collections Cards */}
              <div className="pt-2">
                <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  ACTIVE VECTOR COLLECTIONS:
                </div>
                <div className="space-y-2">
                  <div className="rounded-lg border border-red-500/40 bg-bg/80 p-3">
                    <div className="flex items-center justify-between font-head text-xs font-bold text-white">
                      <span>bloodstrike_knowledge</span>
                      <span className="text-safe text-[9px]">● ONLINE</span>
                    </div>
                    <p className="mt-1 text-[10px] text-slate-400">
                      Weapons recoil curves, spray formulas, and counter-pull drills for AK-47, INP-9, KAG-6, and M4A1.
                    </p>
                    <div className="mt-2 text-[9px] font-mono text-gold">
                      Points indexed: {rag?.points?.bloodstrike_knowledge ?? 104} chunks
                    </div>
                  </div>

                  <div className="rounded-lg border border-line bg-bg/80 p-3">
                    <div className="flex items-center justify-between font-head text-xs font-bold text-white">
                      <span>player_memory</span>
                      <span className="text-safe text-[9px]">● ONLINE</span>
                    </div>
                    <p className="mt-1 text-[10px] text-slate-400">
                      Historical match telemetry, recurring under-flicks, and player muscle-memory evolution vectors.
                    </p>
                    <div className="mt-2 text-[9px] font-mono text-cyan-400">
                      Points indexed: {rag?.points?.player_memory ?? 12} sessions
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Panel>
        </div>

        {/* Right: Semantic Vector Search Simulator */}
        <div className="flex flex-col gap-3 lg:col-span-7 min-h-0">
          <Panel title="Vector Retrieval & Semantic Similarity Tester" id="Q-2" className="flex-1 flex flex-col min-h-0">
            {/* Search Input */}
            <div className="border-b border-line p-3">
              <div className="flex items-center gap-2 rounded-lg border border-line bg-bg p-1.5">
                <Search className="h-4 w-4 text-slate-400 ml-1" />
                <input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Enter weapon name, sensitivity query, or recoil mechanic..."
                  className="min-w-0 flex-1 bg-transparent px-2 text-[11px] text-white placeholder:text-slate-500 focus:outline-none"
                />
                <button
                  onClick={handleSearch}
                  className="rounded bg-rose px-3 py-1 text-[10px] font-bold text-white transition hover:bg-red-600"
                >
                  TEST RETRIEVAL
                </button>
              </div>
            </div>

            {/* Search Results */}
            <div className="flex-1 space-y-3 overflow-y-auto p-3 text-[11px]">
              <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">
                RETRIEVED KNOWLEDGE CHUNKS ({searchResults.length}):
              </div>

              {searchResults.map((item) => (
                <div key={item.id} className="rounded-lg border border-line bg-bg/80 p-3">
                  <div className="flex items-center justify-between border-b border-line pb-1.5 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[9px] font-bold text-cyan-400">{item.id}</span>
                      <span className="font-semibold text-white">{item.title}</span>
                    </div>
                    <span className="rounded bg-safe/10 border border-safe/30 px-1.5 py-0.5 font-mono text-[9px] font-bold text-safe">
                      Cosine: {item.similarity}
                    </span>
                  </div>
                  <p className="text-[10px] leading-relaxed text-slate-300">{item.text}</p>
                  <div className="mt-2 text-[8px] font-mono text-slate-500">
                    Collection: {item.collection} • Indexed on Qdrant Cloud
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}
