# AgenticAim — AI-Powered Esports Aim Coach

> **AMD Developer Hackathon III Project**  
> An agentic, multi-modal esports coaching platform, hands-free neural voice coach, and live hardware advisor powered by **LangGraph**, the **AMD Radeon Cloud Token Factory API**, **Qdrant Cloud Hybrid RAG**, and local edge telemetry tracking.

---

## 📁 Repository Structure

```
AGENTICAIM /
├── AgenticAim/               # Python Backend & Multi-Agent Core
│   ├── main.py               # FastAPI REST API & static web server
│   ├── graph.py              # LangGraph multi-agent state graph + AMD LLM integration
│   ├── tracker.py            # Hardware detection (Winreg/Kernel) & mouse telemetry
│   ├── database.py           # SQLite persistence for 7 Blood Strike sensitivity sliders
│   ├── rag.py                # Qdrant Cloud vector search & player memory
│   ├── config.py             # Hackathon benchmarks & environment config
│   ├── local_voice_coach.py  # Hands-free mic & neural voice comms (Edge TTS)
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # Cyberpunk Esports Web Dashboard
│   ├── src/                  # React 18 + Tailwind CSS components
│   │   ├── components/
│   │   │   ├── CalibrationPanel.jsx # 7 Blood Strike sensitivity calibration sliders
│   │   │   ├── CoachPanel.jsx       # Interactive AI Coach chat & audio visualizer
│   │   │   ├── HardwarePanel.jsx    # Real-time CPU, GPU, RAM & display telemetry
│   │   │   └── MatchPanel.jsx       # Gunfight telemetry & crosshair HUD
│   │   └── App.jsx           # Main dashboard layout & real-time sync
│   ├── package.json          # Node dependencies
│   └── vite.config.js        # Vite bundler configuration
│
└── .gitignore                # Protects secrets (.env), DBs, and virtualenvs
```

---

## 🚀 Key Features

- **🎛️ Official 7 Blood Strike Sensitivity Calibrator**:
  - Automatically calculates and animates recommendations across:
    1. **Camera Sensitivity** (Looking around)
    2. **Firing Sensitivity** (Hipfire recoil control)
    3. **ADS Sensitivity** (Aiming down sights)
    4. **Firing ADS Sensitivity** (Firing while aiming down sights)
    5. **2× Scope Sensitivity** (Mid-range optics)
    6. **4× Scope Sensitivity** (Tactical scopes)
    7. **Sniper Scope Sensitivity** (Long-range precision)
  - Whenever the AI Coach recommends values in chat or analysis, the sliders dynamically slide into the new position!

- **🛡️ Universal Native Windows Hardware Detection**:
  - Dynamically queries Windows Kernel and Registry (`CentralProcessor`, `DriverDesc`, `kernel32`):
    - **CPU**: Real processor string (Intel Core i3/i5/i7/i9 or AMD Ryzen 3/5/7/9).
    - **GPU**: Real graphics card (NVIDIA GeForce RTX/GTX, AMD Radeon, Intel Arc).
    - **RAM**: Motherboard installed physical RAM (8GB, 16GB, 32GB+).
    - **Display**: Screen resolution and refresh rate (e.g. 1920 × 1080 @ 144Hz).
  - Flags high memory load (`[⚠️ UNSAFE TO PLAY - HIGH LOAD]`) to prevent in-game input lag and aim floatiness.

- **💬 Real-Time AI Coach Intelligence (AMD Token Factory)**:
  - Multi-model auto-failover (`DeepSeek-V4.1-Flash`, `DeepSeek-V4-Flash`, `GLM-5.3-Flash`).
  - Grounded in live match telemetry, recoil deltas, and Qdrant pro knowledge with exact slider adjustments.
  - Streaming responses and conversational clarity.

- **🎯 Microsecond Burst Crosshair Vision**:
  - Captures 3–5 frames during trigger pull rather than heavy full-game background recording.
  - Preserves 100% of the player's gaming FPS with zero input lag.

- **🧠 Hybrid RAG + Adaptive Personal Memory (Qdrant Cloud)**:
  - 768-dim semantic vectors indexing weapon recoil patterns (AK47, INP-9, M4A1, KAG-6).
  - Long-term player memory tracking improvement over time.

---

## ⚡ Quickstart

### 1. Configure Secrets
Create `.env` inside `AgenticAim/`:
```ini
AMD_BASE_URL=https://developer.amd.com.cn/radeon/api/v1
AMD_API_KEY=your_amd_api_key_here
AMD_TEXT_MODEL=DeepSeek-V4-Flash
AMD_VISION_MODEL=DeepSeek-V4-Flash-Vision-Exp
AMD_EMBED_MODEL=nomic-embed-text

QDRANT_URL=https://your-cluster-id.europe-west3-0.gcp.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key_here
```

### 2. Start the Backend (Terminal 1)
```bash
cd AgenticAim
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`

### 3. Start the Frontend (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```
- Dashboard: `http://localhost:5173`

---

## 🏆 Hackathon Submission Highlights
- **Multi-Modal AI Pipeline**: Screen Vision + Audio TTS + LLM + Vector RAG.
- **AMD Cloud AI Offloading**: Keeps local client footprint at 0.0% GPU load.
- **Cross-Platform / Universal**: Works on any Intel or AMD machine with any NVIDIA or AMD GPU.
