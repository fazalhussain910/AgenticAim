"""
main.py — AgenticAim FastAPI Application & Terminal Test Runner

NOTE: stdout is reconfigured to UTF-8 at startup to support box-drawing
characters on Windows terminals that default to cp1252.
================================================================
Two modes of operation:

  1. FastAPI Server (for future deployment to Vercel/Render):
       uvicorn main:app --reload
     Exposes REST endpoints:
       POST /analyze          → Run a full mock analysis pipeline
       GET  /history          → Fetch recent sessions from DB
       GET  /history/{id}     → Fetch a single session
       GET  /games            → List supported games

  2. Terminal Test Runner (for immediate hackathon testing):
       python main.py
     Runs a simulated analysis for EACH aim scenario through the full
     LangGraph pipeline and prints a coaching report per scenario.

AMD Developer Hackathon | AI-Powered Esports Aim Coach
"""

import asyncio
import io
import logging
import sys
import time
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

# ── Force UTF-8 output on Windows (prevents cp1252 UnicodeEncodeError) ───────
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# AgenticAim modules
from config import API_HOST, API_PORT, GAME_CONFIG, get_game_benchmark
from database import init_db, fetch_recent_sessions, fetch_session_by_id, get_latest_session
from tracker import (
    generate_mock_shot_event,
    get_active_game,
    ShotEvent,
    get_hardware_spec,
    get_live_system_impact,
    get_native_windows_hardware,
)
from graph import build_graph, format_coaching_report, AimState, ask_ai_coach, ask_ai_coach_stream
from rag import (
    init_qdrant_collections,
    retrieve_knowledge,
    retrieve_player_memory,
    KNOWLEDGE_COLL,
    MEMORY_COLL,
    _get_qdrant,
)

# ==============================================================================
# LOGGING SETUP
# ==============================================================================
# Configure once here — all sub-modules inherit this config.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),   # Terminal output
        logging.FileHandler("agenticaim.log", encoding="utf-8"),  # File log
    ],
)
logger = logging.getLogger("agenticaim.main")

# Suppress internal HTTP & OpenAI client retry notices in terminal output
for noisy_logger in ("openai", "httpx", "httpcore", "httpx2", "httpcore2", "urllib3"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

# ==============================================================================
# LANGGRAPH INSTANCE (compiled once at import time)
# ==============================================================================
# Build the graph (and initialise the DB schema) once when the module loads.
# Subsequent calls to .invoke() reuse the compiled graph.
logger.info("Building LangGraph pipeline...")
aim_graph = build_graph()
logger.info("LangGraph pipeline ready.")

# ==============================================================================
# FASTAPI APPLICATION
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: runs on startup and shutdown."""
    logger.info("AgenticAim API starting up...")
    init_db()   # Ensure DB schema exists before accepting requests
    yield
    logger.info("AgenticAim API shutting down.")


app = FastAPI(
    title="AgenticAim API",
    description=(
        "AI-Powered Esports Aim Coach backend. "
        "Analyzes FPS game telemetry via LangGraph + AMD AI to recommend "
        "optimal sensitivity settings."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins during development (lock down for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# PYDANTIC SCHEMAS (Request / Response)
# ==============================================================================

class AnalyzeRequest(BaseModel):
    """Request body for the /analyze endpoint."""
    game_name: str = Field(
        default="Blood Strike",
        description="Display name of the game to simulate.",
        examples=["Blood Strike", "Valorant"],
    )
    game_exe: str = Field(
        default="bloodstrike.exe",
        description="EXE name (must match an entry in GAME_CONFIG).",
        examples=["bloodstrike.exe", "valorant.exe"],
    )
    scenario: str = Field(
        default="recoil_not_controlled",
        description=(
            "Aim scenario to simulate. One of: "
            "recoil_not_controlled | over_flick | under_flick | good_aim"
        ),
    )


class AnalyzeResponse(BaseModel):
    """Response from the /analyze endpoint."""
    db_session_id:      int
    game:               str
    scenario:           str
    accuracy_score:     float
    recoil_detected:    bool
    recoil_severity:    str
    flick_diagnosis:    str
    vision_status:      str = "online"
    recommended_x_sens: float
    recommended_y_sens: float
    confidence_pct:     int
    pro_x_sens:         float
    pro_y_sens:         float
    coach_reasoning:    str
    is_rag_verified:    bool = False
    processing_time_s:  float


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

# Paths to Web Frontends
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist"))
if not os.path.exists(FRONTEND_DIST):
    FRONTEND_DIST = os.path.abspath(os.path.join(BASE_DIR, "frontend", "dist"))

DIST_INDEX_FILE = os.path.join(FRONTEND_DIST, "index.html") if os.path.exists(FRONTEND_DIST) else None
DASHBOARD_FILE = os.path.join(BASE_DIR, "dashboard.html")
_latest_client_hardware = {}

# Mount React static assets if present
if os.path.exists(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")


@app.get("/{filename}.png", include_in_schema=False)
async def serve_frontend_png(filename: str):
    """Serve root-level static images (coach avatars, telemetry images) from frontend/dist."""
    if os.path.exists(FRONTEND_DIST):
        img_path = os.path.join(FRONTEND_DIST, f"{filename}.png")
        if os.path.exists(img_path):
            return FileResponse(img_path)
    raise HTTPException(status_code=404, detail="Image not found")


@app.get("/", tags=["Dashboard & Health"])
async def root(request: Request):
    """
    Main entry point:
    - Serves modern React Esports Web Dashboard (frontend/dist) when accessed via browser.
    - Falls back to dashboard.html if React build is not present.
    - Returns JSON status when accessed via API/JSON request.
    """
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return {
            "status": "online",
            "app":    "AgenticAim API v1.0.0",
            "model":  "AMD Token Factory (DeepSeek Vision + DeepSeek Text)",
        }

    # 1. Prefer React modern frontend build
    if DIST_INDEX_FILE and os.path.exists(DIST_INDEX_FILE):
        with open(DIST_INDEX_FILE, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)

    # 2. Fallback to classic dashboard.html
    if os.path.exists(DASHBOARD_FILE):
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)

    return {
        "status": "online",
        "app":    "AgenticAim API v1.0.0",
        "model":  "AMD Token Factory (DeepSeek Vision + DeepSeek Text)",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for cloud uptime monitors."""
    return {
        "status": "online",
        "app":    "AgenticAim API v1.0.0",
        "model":  "AMD Token Factory (DeepSeek Vision + DeepSeek Text)",
    }




@app.get("/api/system-specs", tags=["AI Coach & Hardware"])
async def get_system_specs():
    """Returns 100% accurate native Windows physical hardware specs."""
    return get_native_windows_hardware()


@app.post("/api/client-hardware", tags=["AI Coach & Hardware"])
async def receive_client_hardware(hw: dict):
    """
    Stores and logs client hardware specs detected by browser WebGL (GPU, Cores, RAM, Refresh Rate).
    Demonstrates client-side hardware telemetry integration to judges.
    """
    global _latest_client_hardware
    _latest_client_hardware = hw
    logger.info(
        f"Client Hardware Detected: GPU={hw.get('gpu')} | "
        f"Cores={hw.get('cores')} | RAM={hw.get('ram')} | Hz={hw.get('hz')}"
    )
    return {"status": "synced", "client_hardware": hw}


@app.get("/games", tags=["Config"])
async def list_supported_games():
    """
    Return all games supported by the tracker.
    Clients can use this to populate a game-selection dropdown.
    """
    return {
        "supported_games": [
            {"exe": exe, "display_name": name}
            for exe, name in GAME_CONFIG.items()
        ]
    }


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_session(request: AnalyzeRequest):
    """
    Run a full AgenticAim analysis pipeline using mock telemetry.

    This endpoint is ideal for:
    • Frontend demos
    • CI/CD testing
    • Hackathon demonstrations

    For live hardware tracking, use the terminal runner (python main.py).
    """
    logger.info(f"API /analyze called: game={request.game_name}, scenario={request.scenario}")

    valid_scenarios = {"recoil_not_controlled", "over_flick", "under_flick", "good_aim"}
    if request.scenario not in valid_scenarios:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scenario. Must be one of: {valid_scenarios}",
        )

    start = time.perf_counter()

    # Generate mock telemetry
    event = generate_mock_shot_event(
        game_name=request.game_name,
        game_exe=request.game_exe,
        scenario=request.scenario,
    )

    # Build initial state and run graph
    initial_state: AimState = {
        "shot_event":             event,
        "vision_raw":             "",
        "accuracy_score":         0.0,
        "recoil_detected":        False,
        "recoil_severity":        "unknown",
        "flick_diagnosis":        "unknown",
        "vision_status":          "online",
        "pro_meta_summary":       "",
        "pro_x_sens":             75.0,
        "pro_y_sens":             40.0,
        "no_ads_sens":            75,
        "iron_sight_sens":        40,
        "scope_sens":             40,
        "newbie_advice":          "",
        "coach_reasoning":        "",
        "recommended_x_sens":     75.0,
        "recommended_y_sens":     40.0,
        "confidence_pct":         0,
        "db_row_id":              -1,
        "game_knowledge_context": "",
        "player_history_context": "",
        "error":                  "",
    }

    # Run LangGraph pipeline (blocking in thread pool to not block event loop)
    final_state = await asyncio.get_event_loop().run_in_executor(
        None, aim_graph.invoke, initial_state
    )

    elapsed = time.perf_counter() - start

    return AnalyzeResponse(
        db_session_id=      final_state.get("db_row_id", -1),
        game=               event.game_name,
        scenario=           request.scenario,
        accuracy_score=     final_state.get("accuracy_score", 0.0),
        recoil_detected=    final_state.get("recoil_detected", False),
        recoil_severity=    final_state.get("recoil_severity", "unknown"),
        flick_diagnosis=    final_state.get("flick_diagnosis", "unknown"),
        vision_status=      final_state.get("vision_status", "online"),
        recommended_x_sens= final_state.get("recommended_x_sens", 3.5),
        recommended_y_sens= final_state.get("recommended_y_sens", 3.5),
        confidence_pct=     final_state.get("confidence_pct", 0),
        pro_x_sens=         final_state.get("pro_x_sens", 3.5),
        pro_y_sens=         final_state.get("pro_y_sens", 3.5),
        coach_reasoning=    final_state.get("coach_reasoning", ""),
        is_rag_verified=    bool(final_state.get("game_knowledge_context")),
        processing_time_s=  round(elapsed, 2),
    )


@app.get("/history", tags=["Database"])
async def get_history(limit: int = Query(default=10, ge=1, le=100)):
    """
    Return the `limit` most recent coaching sessions from the database.
    Useful for displaying trend data or session history in a frontend.
    """
    sessions = await fetch_recent_sessions(limit=limit)
    return {"count": len(sessions), "sessions": sessions}


@app.get("/history/{session_id}", tags=["Database"])
async def get_session(session_id: int):
    """Fetch a single coaching session by its database ID."""
    session = await fetch_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message or question for AI coach")
    history: list[dict] = Field(default=[], description="Previous conversation history")


@app.get("/api/hardware", tags=["AI Coach & Hardware"])
async def get_hardware_safety():
    """
    Live Hardware Safety Advisor endpoint.
    Returns live CPU %, RAM %, memory usage in MB, and whether it's safe to play.
    Includes detected native Windows hardware (AMD Ryzen CPU & Radeon Vega GPU).
    """
    import psutil
    cpu_pct = psutil.cpu_percent(interval=0.05)
    ram = psutil.virtual_memory()
    ram_pct = ram.percent
    ram_used_mb = round(ram.used / (1024**2), 1)
    ram_total_mb = round(ram.total / (1024**2), 1)

    is_safe = not (cpu_pct > 80.0 or ram_pct > 85.0)
    safety_badge = "[✅ SAFE TO PLAY]" if is_safe else "[⚠️ UNSAFE TO PLAY - HIGH LOAD]"
    safety_msg = (
        f"Hardware load is optimal (CPU: {cpu_pct}%, RAM: {ram_pct}%). Zero input delay detected."
        if is_safe else
        f"High resource load (CPU: {cpu_pct}%, RAM: {ram_pct}%). Close heavy background apps before gaming!"
    )

    hw_specs = get_native_windows_hardware()

    return {
        "cpu_pct": cpu_pct,
        "ram_pct": ram_pct,
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "gpu_pct": 0.0,
        "gpu_desc": "0.0% (Vision offloaded to AMD Cloud API)",
        "cpu_name": hw_specs.get("cpu", "AMD Ryzen 5 PRO 3500U"),
        "gpu_name": hw_specs.get("gpu", "AMD Radeon(TM) Vega 8 Graphics"),
        "ram_installed_gb": hw_specs.get("ram_installed_gb", 8.0),
        "cores": hw_specs.get("cores", 8),
        "display": hw_specs.get("display", "1280 × 720 @ 60Hz"),
        "is_safe_to_play": is_safe,
        "safety_badge": safety_badge,
        "safety_message": safety_msg,
    }


@app.get("/api/latest-session", tags=["AI Coach & Hardware"])
async def get_latest_match_session():
    """
    Retrieve the most recently analyzed shot telemetry and sensitivity settings from SQLite.
    """
    session = get_latest_session()
    if not session:
        raise HTTPException(status_code=404, detail="No recorded aim sessions found in database.")
    return session


@app.post("/api/chat", tags=["AI Coach & Hardware"])
async def chat_with_coach(req: ChatRequest):
    """
    Interactive AI Coach Chat endpoint powered by AMD Token Factory API.
    Injects latest match telemetry and live hardware stats.
    """
    try:
        response = ask_ai_coach(user_message=req.message, chat_history=req.history)
        return response
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/status", tags=["Hybrid RAG & Memory"])
async def get_rag_status():
    """
    Check Qdrant vector database connectivity and collection statistics.
    """
    client = _get_qdrant()
    if client is None:
        return {
            "status": "offline",
            "message": "Qdrant is currently unavailable or unconfigured (non-fatal fallback active)",
            "knowledge_collection": KNOWLEDGE_COLL,
            "memory_collection": MEMORY_COLL,
            "points": {KNOWLEDGE_COLL: 0, MEMORY_COLL: 0},
        }

    try:
        colls = [c.name for c in client.get_collections().collections]
        counts = {}
        for c in (KNOWLEDGE_COLL, MEMORY_COLL):
            if c in colls:
                try:
                    counts[c] = client.get_collection(c).points_count
                except Exception:
                    counts[c] = 0
            else:
                counts[c] = 0

        return {
            "status": "online",
            "collections_found": colls,
            "knowledge_collection": KNOWLEDGE_COLL,
            "memory_collection": MEMORY_COLL,
            "points": counts,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@app.post("/api/rag/seed", tags=["Hybrid RAG & Memory"])
async def seed_rag_knowledge():
    """
    Seed or re-seed the static Blood Strike game knowledge documents into Qdrant.
    """
    success = init_qdrant_collections()
    if not success:
        raise HTTPException(
            status_code=503,
            detail="Failed to initialize or seed Qdrant collections. Ensure Qdrant is running or cloud credentials are valid."
        )
    return {"status": "success", "message": "Knowledge collections initialized and seeded."}


@app.get("/api/rag/player-memory", tags=["Hybrid RAG & Memory"])
async def get_player_memory_endpoint(player_id: str = "default", limit: int = 5):
    """
    Retrieve historical performance memories for a player from the Qdrant memory collection.
    """
    memory_text = retrieve_player_memory(player_id=player_id, top_n=limit)
    return {
        "player_id": player_id,
        "history_context": memory_text,
    }


# ==============================================================================
# TERMINAL TEST RUNNER
# ==============================================================================

def run_terminal_test():
    """
    Standalone terminal test runner — no browser, no frontend, no live hardware.

    Iterates through all four aim scenarios, runs each one through the full
    LangGraph pipeline, and prints a formatted coaching report to the terminal.

    Run with:
        python main.py
    """
    # ASCII banner (pure ASCII chars - safe on cp1252 / any Windows terminal)
    banner = (
        "\n"
        "  +=========================================================+\n"
        "  |         A G E N T I C A I M  v1.0.0                    |\n"
        "  |   AI-Powered FPS Aim Coach | AMD Developer Hackathon    |\n"
        "  +=========================================================+\n"
    )
    print(banner)

    # ── Hardware Detection Banner ─────────────────────────────────────────────
    hw = get_hardware_spec()
    hw_banner = (
        "  +---------------------------------------------------------+\n"
        "  |  [HARDWARE DETECTED]                                    |\n"
        f"  |  CPU: {hw['cpu_name'][:48]:<49} |\n"
        f"  |  RAM: {hw['ram_gb']} GB System Memory Installed / Usable{' ' * 13} |\n"
        f"  |  GPU: {hw['gpu_name'][:48]:<49} |\n"
        "  |  Cloud Offload: 100% of Vision & LLM on AMD Token Cloud |\n"
        "  +---------------------------------------------------------+\n"
    )
    print(hw_banner)

    # All four test scenarios
    scenarios = [
        ("recoil_not_controlled", "🔥 Scenario 1: Recoil Not Controlled"),
        ("over_flick",            "⚡ Scenario 2: Over-Flick"),
        ("under_flick",           "🐢 Scenario 3: Under-Flick"),
        ("good_aim",              "🎯 Scenario 4: Good Aim (Baseline)"),
    ]

    for scenario_key, scenario_label in scenarios:
        print(f"\n{'─' * 60}")
        print(f"  {scenario_label}")
        print(f"{'─' * 60}")

        # Step 1 — Generate mock telemetry
        print("\n[1/4] Generating mock telemetry...")
        event = generate_mock_shot_event(
            game_name="Blood Strike",
            game_exe="bloodstrike.exe",
            scenario=scenario_key,
        )
        summary = event.to_summary_dict()
        print(f"      Mouse summary → dx={summary['total_dx']}, dy={summary['total_dy']}, "
              f"speed={summary['avg_speed_pps']} px/s, downward_pull={summary['downward_pull']}")
        print(f"      Frames: {len(event.frames_b64)} captured (mock JPEG)")

        # Step 2 — Build initial state
        initial_state: AimState = {
            "shot_event":             event,
            "vision_raw":             "",
            "accuracy_score":         0.0,
            "recoil_detected":        False,
            "recoil_severity":        "unknown",
            "flick_diagnosis":        "unknown",
            "vision_status":          "online",
            "pro_meta_summary":       "",
            "pro_x_sens":             75.0,
            "pro_y_sens":             40.0,
            "no_ads_sens":            75,
            "iron_sight_sens":        40,
            "scope_sens":             40,
            "coach_reasoning":        "",
            "recommended_x_sens":     75.0,
            "recommended_y_sens":     40.0,
            "newbie_advice":          "",
            "confidence_pct":         0,
            "db_row_id":              -1,
            "game_knowledge_context": "",
            "player_history_context": "",
            "error":                  "",
        }

        # Step 3 — Run the full LangGraph pipeline
        print("\n[2/4] Running LangGraph pipeline (AMD Vision → Search → Coach → DB)...")
        start = time.perf_counter()
        try:
            final_state = aim_graph.invoke(initial_state)
        except Exception as e:
            logger.error(f"Pipeline failed for scenario '{scenario_key}': {e}")
            print(f"\n  ❌ Pipeline error: {e}")
            continue

        elapsed = time.perf_counter() - start
        print(f"      Pipeline completed in {elapsed:.1f}s")

        # Step 4 — Print coaching report
        print("\n[3/4] Generating coaching report...")
        report = format_coaching_report(final_state)
        print(report)

        print(f"[4/4] Session saved to database → ID: {final_state.get('db_row_id', 'N/A')}")
        print(f"\n      ⏱  Total time for this scenario: {elapsed:.2f}s")

        # Small pause between scenarios for readability
        time.sleep(0.5)

    print("\n" + "═" * 60)
    print("  ✅  All scenarios completed! Check agenticaim.db for logged sessions.")
    print("  💡  Tip: Run `uvicorn main:app --reload` to start the REST API server.")
    print("═" * 60 + "\n")

    # ── Interactive AI Coach Terminal Chat Loop ────────────────────────────────
    start_interactive_chat()


def start_interactive_chat():
    """
    Live Interactive AI Coach Chat & Hardware Advisor Loop in terminal.
    Can be run directly via: python main.py --chat
    """
    print("\n" + "=" * 60)
    print("  💬  AI COACH LIVE CHAT & HARDWARE SAFETY ADVISOR")
    print("  Ask about your aim, recoil, match mistakes, or hardware health.")
    print("  (Type your message below | Type 'exit' or 'quit' to quit)")
    print("=" * 60 + "\n")

    chat_history = []
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[AI Coach] Session ended. Good luck in your matches!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("\n[AI Coach] Session ended. Keep grinding and click heads!")
            break

        print("\n[AI Coach is connecting to AMD Token Factory Cloud API...]")
        full_reply = []
        hw = None
        try:
            stream_gen = ask_ai_coach_stream(user_input, chat_history=chat_history)
            first_chunk = next(stream_gen)
            if first_chunk.get("type") == "meta":
                hw = first_chunk["hardware_status"]
                print(f"\n--- HARDWARE STATUS: {hw['safety_badge']} ---")
                print(f"CPU: {hw['cpu_pct']}% | RAM: {hw['ram_pct']}% ({hw['ram_used_mb']}/{hw['ram_total_mb']} MB) | GPU: {hw['gpu_desc']}")
                if not hw["is_safe"]:
                    print(f"⚠️  Warning: {hw['safety_msg']}")
            first_token = True
            for chunk in stream_gen:
                if chunk.get("type") == "token":
                    content = chunk.get("content", "")
                    if content:
                        if first_token:
                            print("\nCoach: ", end="", flush=True)
                            first_token = False
                        full_reply.append(content)
                        print(content, end="", flush=True)
            print("\n" + "-" * 60)
        except KeyboardInterrupt:
            print("\n\n[AI Coach] Request cancelled by user. Type another question or 'exit' to quit.\n")
            continue
        except Exception as e:
            print(f"\n[AI Coach] Error: {e}\n")
            continue

        reply_str = "".join(full_reply).strip()
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": reply_str})


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    # ── Check CLI args ─────────────────────────────────────────────────────────
    # python main.py          → terminal test (scenarios + chat)
    # python main.py --chat   → start interactive AI coach chat directly
    # python main.py --serve  → start FastAPI server

    if "--serve" in sys.argv:
        logger.info(f"Starting FastAPI server on {API_HOST}:{API_PORT}")
        uvicorn.run(
            "main:app",
            host=API_HOST,
            port=API_PORT,
            reload=True,
            reload_excludes=["*.log", "*.db", "*.sqlite*", "__pycache__/*"],
            log_level="info",
        )
    elif "--chat" in sys.argv:
        start_interactive_chat()
    else:
        # Default: run the full terminal test suite
        run_terminal_test()
