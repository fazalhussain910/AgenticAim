# AgenticAim — AI-Powered Esports Aim Coach

> **AMD Developer Hackathon III Project**  
> An agentic, multi-modal esports coaching platform, hands-free neural voice coach, and live hardware advisor powered by **LangGraph**, the **AMD Radeon Cloud Token Factory API**, **Qdrant Cloud Hybrid RAG**, and local edge telemetry tracking.

---

## 🚀 Key Features

- **🎙️ Real-Time Neural Voice AI Coach (`local_voice_coach.py`)**:
  - **Hands-Free Esports Comms**: Captures player voice via headset mic (`SpeechRecognition`) or keyboard mode with automatic fallback.
  - **Ultra-Realistic Voice Synthesis**: Powered by Microsoft Edge Neural TTS (`en-US-ChristopherNeural` at `+15%` rate) for crisp, human-like coach callouts played instantly through `pygame.mixer`.
  - **Zero Local GPU Overhead**: No heavy Whisper models locally; audio transcription and cloud LLM inference run with near-zero local CPU/GPU load.

- **💬 Context-Aware AI Coach Intelligence**:
  - **Conversational Queries**: Responds naturally, playfully, and concisely to casual chatter (*"How are you?", "What's up?"*) without forcing telemetry.
  - **Gameplay Queries**: Grounded in live match telemetry, recoil deltas, and Qdrant pro knowledge with exact slider adjustments.
  - **Fast Esports Comms Tempo**: Strictly under 3 sentences for rapid in-game callouts.
  - Powered by AMD Token Factory Cloud API (`DeepSeek-V4-Flash` / `DeepSeek-V4.1-Flash`) with word-by-word streaming.

- **🧠 Hybrid RAG + Adaptive Personal Memory (Qdrant Cloud)**:
  - **Blood Strike Vector Knowledge Base (`bloodstrike_knowledge`)**: 768-dim semantic vectors (`nomic-embed-text`) indexing pro weapon recoil patterns (AK47, INP-9, M4A1, KAG-6), sensitivity formulas, and counter-pull drills.
  - **Automated Seeder (`auto_seed_qdrant.py`)**: One-command ingestion from structured pro guides (`bloodstrike_pro_guide.txt`) to Qdrant Cloud.
  - **Long-Term Player Memory (`player_memory`)**: Chronological session history and recurring issue tracking with deterministic UUID idempotency.
  - **Measurable Outcome Rule**: Pro coach compares current gunfight numbers (`dx`, `dy`, `downward_pull`, `accuracy`) against prior sessions — never praises without measurable data!

- **🛡️ Live Hardware Safety Advisor**:
  - Continuous local hardware profiling (`psutil`) measuring CPU %, RAM % (used vs. total MB), and GPU offload.
  - Pre-match safety threshold badges: `[✅ SAFE TO PLAY]` vs `[⚠️ UNSAFE TO PLAY - HIGH LOAD]`.
  - Warns players before ranked queues if high RAM load will induce micro-stutters and mouse input delay.

- **🎯 Multimodal Visual Analysis with 5s Fail-Safe**:
  - Inspects crosshair drift, muzzle flash rise, and target tracking using `DeepSeek-V4-Flash-Vision-Exp` on AMD Token Factory Cloud.
  - Evaluates recoil kick, flick classification (over-flick, under-flick, tracking), and shot accuracy.
  - **5-Second Crash-Proof Fallback**: Prevents any hanging or crash if screen capture or vision endpoints experience network latency.

- **🎛️ Blood Strike In-Game Slider Calibration**:
  - Translates telemetry into exact in-game slider adjustments:
    - **No ADS Steering (Hipfire)** (Baseline: 75)
    - **Iron Sight / Holo / Red Dot** (Baseline: 40)
    - **Scopes (2X to 8X)** (Baseline: 40)

- **🔒 Safe-by-Design Anti-Cheat Compliance**:
  - Zero game memory hooking, zero DLL injection, zero full-game recording.
  - Processes only discrete 1-second gunfight crosshair bursts and mouse movement deltas.

---

## 🏗️ Architecture Overview

```
                      ┌────────────────────────────────────────┐
                      │            AgenticAim Client           │
                      │  (AMD Ryzen APU / Edge Telemetry)      │
                      └──────────────────┬─────────────────────┘
                                         │
                         Left-Click Telemetry + Crosshair Frames
                         OR Live Headset Mic Voice Query
                                         │
                                         ▼
                      ┌────────────────────────────────────────┐
                      │       LangGraph Multi-Agent Pipeline   │
                      │                                        │
                      │  [1] Vision Analyst (5s Fail-Safe)     │ ──► AMD Cloud Vision
                      │  [2] Retrieve Game Knowledge (RAG)     │ ◄── Qdrant Cloud (768-dim)
                      │  [3] Retrieve Player Memory (RAG)      │ ◄── Historical Telemetry
                      │  [4] Aim Coach Calculator (Math+LLM)   │ ──► DeepSeek-V4-Flash (AMD)
                      │  [5] SQLite Database Logger            │ ──► agenticaim.db
                      │  [6] Store Session Memory (RAG)        │ ──► Qdrant Idempotent Upsert
                      └──────────────────┬─────────────────────┘
                                         │
                         Calibrated Sliders & Tailored Coaching
                                         │
                                         ▼
                      ┌────────────────────────────────────────┐
                      │    AI Coach Live Output Interfaces     │
                      │                                        │
                      │  • Neural Voice Coach (Edge TTS)       │ ──► Player Headset Audio
                      │  • Terminal Streamer (Token-by-Token)  │
                      │  • REST API (FastAPI + Swagger Docs)   │ ──► Web / GUI Frontends
                      │  • Hardware Safety HUD (psutil)        │
                      └────────────────────────────────────────┘
```

---

## ⚡ Quickstart for Team Members

### 1. Clone the Repository
```bash
git clone https://github.com/fazalhussain910/AgenticAim.git
cd AgenticAim
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your AMD Token Factory credentials and Qdrant settings:
```ini
AMD_BASE_URL=https://developer.amd.com.cn/radeon/api/v1
AMD_API_KEY=your_actual_amd_api_key_here
AMD_TEXT_MODEL=DeepSeek-V4-Flash
AMD_VISION_MODEL=DeepSeek-V4-Flash-Vision-Exp
AMD_EMBED_MODEL=nomic-embed-text

# Qdrant Cloud (Recommended) or Local Docker
QDRANT_URL=https://YOUR_CLUSTER_ID.europe-west3-0.gcp.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_cloud_api_key_here
```

### 5. Seed Qdrant Vector Knowledge Base
Ingest the curated pro meta guides (`bloodstrike_pro_guide.txt`) into Qdrant Cloud:
```bash
python auto_seed_qdrant.py
```

---

## 🎮 Running AgenticAim

### 🎙️ Mode 1: Live Voice AI Coach (Hands-Free Mic + Neural Audio)
Run the real-time voice coaching loop with Microsoft Edge Neural TTS:
```bash
python local_voice_coach.py
```
- **Option 1**: Speak directly into your headset microphone hands-free.
- **Option 2**: Type your questions and hear the Coach speak back in real time.

### 💬 Mode 2: Interactive AI Coach Chat & Hardware Advisor (CLI)
Jump directly into the live coaching terminal with real-time token streaming:
```bash
python main.py --chat
```
Ask questions like:
- *"How are you doing today Coach?"*
- *"Why is my AK47 recoil pulling too far up and right?"*
- *"What Blood Strike sensitivity sliders should I use for INP-9?"*
- *"Is my PC safe to play ranked right now?"*

### 🚀 Mode 3: Start FastAPI REST Backend (For Web & Desktop GUI)
Starts the high-performance REST backend with interactive Swagger documentation:
```bash
python main.py --serve
```
- Swagger API Docs: 👉 `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/`

### 🧪 Mode 4: Run Full LangGraph Pipeline Benchmark
Runs 4 benchmark esports scenarios (Over-flick, Heavy Recoil, Clean Burst, Under-flick):
```bash
python main.py
```

---

## 📡 REST API Endpoints (For Frontend & GUI Developers)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/hardware` | Returns real-time CPU %, RAM % (used vs. total MB), GPU load, and `is_safe_to_play` badge. |
| `GET` | `/api/latest-session` | Returns the latest match telemetry, vision diagnosis, and recommended Blood Strike slider settings. |
| `POST` | `/api/chat` | Send `{ "message": "...", "history": [...] }` to chat with the AI Coach (returns `reply`, `is_rag_verified`, `sources`). |
| `GET` | `/api/rag/status` | Check Qdrant vector DB connection, collection statistics, and point counts. |
| `POST` | `/api/rag/seed` | Seed/re-seed static Blood Strike game knowledge chunks into Qdrant vector collection. |
| `GET` | `/api/rag/player-memory` | Retrieve chronological historical performance memories for a player. |
| `GET` | `/history` | Fetch recent logged match sessions from `agenticaim.db`. |
| `GET` | `/history/{id}` | Fetch a single coaching session by database ID. |
| `GET` | `/games` | List supported FPS titles and config mappings. |
| `GET` | `/` | Health check endpoint and API metadata. |

---

## 🛠️ Tech Stack

- **Reasoning & Vision Models**: DeepSeek-V4-Flash & DeepSeek-V4-Flash-Vision-Exp on AMD Radeon Token Factory Cloud.
- **Voice AI & Neural Audio**: `edge-tts` (`en-US-ChristopherNeural`), `SpeechRecognition`, `PyAudio`, `pygame.mixer`.
- **Vector Database & Hybrid RAG**: Qdrant Cloud (`bloodstrike_knowledge`, `player_memory`) with 768-dim `nomic-embed-text` vectors and deterministic SHA-256 fallback.
- **Agent Orchestration**: LangGraph, LangChain Core.
- **Edge Profiling**: `psutil` (Hardware Safety), `pynput` (Mouse Telemetry), `mss` (Screen Bursts).
- **Web API & Serving**: FastAPI, Uvicorn, Pydantic v2.
- **Database**: SQLite3 (`agenticaim.db`) with automatic migration schema.
- **Platform**: Optimized for AMD Ryzen APU & Radeon Vega Graphics on Windows 11.
