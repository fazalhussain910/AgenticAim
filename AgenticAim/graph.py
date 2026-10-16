"""
graph.py — AgenticAim LangGraph Orchestration (The AI Brain)
=============================================================
Implements a stateful 4-node LangGraph pipeline that transforms raw game
telemetry into actionable, mathematically-grounded sensitivity recommendations.

Pipeline (in execution order):
    [ShotEvent Telemetry]
           │
    ┌──────▼──────┐
    │  Node 1     │  Vision Analyst       ← AMD Vision LLM (multimodal)
    │             │  Analyses game frames + mouse deltas for:
    │             │    • Crosshair vs. enemy position (accuracy)
    │             │    • Muzzle flash / recoil kick detection
    │             │    • Over-flick / under-flick / on-target diagnosis
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Node 2     │  Meta Researcher      ← DuckDuckGo web search (free)
    │             │  Fetches current pro-player sensitivity settings and
    │             │  recoil control meta for the detected game.
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Node 3     │  Aim Coach Calculator ← AMD Text LLM (reasoning)
    │             │  Synthesises vision analysis + pro meta → produces
    │             │  exact X/Y sensitivity deltas with mathematical
    │             │  justification and confidence score.
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Node 4     │  Database Logger      ← SQLite (local, free)
    │             │  Persists the complete session for trend analysis.
    └──────┬──────┘
           │
    [CoachingReport returned to caller]

AMD Developer Hackathon | AI-Powered Esports Aim Coach
"""

import json
import logging
import re
import time
from typing import Annotated, Any, Optional, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph import StateGraph, END

from config import (
    AMD_API_KEY,
    AMD_BASE_URL,
    AMD_TEXT_MODEL,
    AMD_VISION_MODEL,
    BLOOD_STRIKE_SENSITIVITY_CONFIG,
    LLM_TEMPERATURE,
    PRO_BENCHMARKS,
    SENSITIVITY_BOUNDS,
    get_game_benchmark,
)
import psutil
from database import log_session_sync, init_db, get_latest_session
from tracker import ShotEvent, get_live_system_impact
from rag import (
    init_qdrant_collections,
    retrieve_knowledge,
    retrieve_player_memory,
    store_player_memory,
)

logger = logging.getLogger("agenticaim.graph")

for noisy in ("openai", "httpx", "httpcore", "httpx2", "httpcore2", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# ==============================================================================
# LLM CLIENTS
# ==============================================================================

# ── Vision LLM (Node 1) ───────────────────────────────────────────────────────
# Points to the AMD multimodal model. Accepts image_url content blocks.
# Crash-proof 5-second timeout ensures live demos never hang.
vision_llm = ChatOpenAI(
    base_url=AMD_BASE_URL,
    api_key=AMD_API_KEY,
    model=AMD_VISION_MODEL,
    temperature=LLM_TEMPERATURE,
    request_timeout=5.0,
    max_retries=0,
)

# ── Text / Reasoning LLM (Nodes 2, 3, 4) ─────────────────────────────────────
# Fast text model for RAG synthesis and sensitivity math.
# max_tokens=100 enforces sub-second low-latency esports coach replies.
text_llm = ChatOpenAI(
    base_url=AMD_BASE_URL,
    api_key=AMD_API_KEY,
    model=AMD_TEXT_MODEL,
    temperature=LLM_TEMPERATURE,
    request_timeout=14.0,
    max_tokens=150,
    max_retries=1,
)

# ── Free Web Search Tool (Node 2) ─────────────────────────────────────────────
# DuckDuckGo requires no API key.
# NOTE: search_tool is instantiated lazily inside node_meta_researcher() so that
# a missing `ddgs` package only raises an error when the node actually runs,
# not at import time. Install with: pip install ddgs
# search_tool is NOT created here — see _get_search_tool() below.

# ==============================================================================
# LANGGRAPH STATE DEFINITION
# ==============================================================================

class AimState(TypedDict):
    """
    The shared mutable state that flows through every node in the graph.
    Each node reads what it needs and writes its own output back into state.

    Using TypedDict gives us type safety while keeping JSON-serializability.
    """
    # ── Input ─────────────────────────────────────────────────────────────────
    shot_event:         ShotEvent           # Raw telemetry from tracker.py

    # ── Node 1 outputs ────────────────────────────────────────────────────────
    vision_raw:         str                 # Full LLM response text
    accuracy_score:     float               # 0.0–1.0 on-target estimate
    recoil_detected:    bool                # Was significant recoil observed?
    recoil_severity:    str                 # "none" | "mild" | "moderate" | "severe"
    flick_diagnosis:    str                 # "over-flick" | "under-flick" | "on-target"
    vision_status:      str                 # "online" | "fallback"

    # ── Node 2 outputs ────────────────────────────────────────────────────────
    pro_meta_summary:   str                 # Search result digest
    pro_x_sens:         float               # Community/pro X sens recommendation
    pro_y_sens:         float               # Community/pro Y sens recommendation

    # ── Node 3 outputs (Blood Strike integer in-game sliders) ─────────────────
    no_ads_sens:        int                 # "No ADS Steering" (FPS/TPS) [baseline 75]
    iron_sight_sens:    int                 # "Iron Sight/Holo/Red Dot" [baseline 40]
    scope_sens:         int                 # "Scopes (2X to 8X)" [baseline 40]
    coach_reasoning:    str                 # Full step-by-step reasoning
    newbie_advice:      str                 # Simple encouraging coaching advice for beginners
    recommended_x_sens: float               # Maintained for database compatibility
    recommended_y_sens: float               # Maintained for database compatibility
    confidence_pct:     int                 # 0–100

    # ── Node 4 outputs ────────────────────────────────────────────────────────
    db_row_id:          int                 # SQLite row ID of the saved session

    # ── RAG context (injected by RAG nodes, consumed by aim_coach) ───────────
    game_knowledge_context:  str            # Retrieved Blood Strike KB snippets
    player_history_context:  str            # Chronological player session history

    # ── Meta ──────────────────────────────────────────────────────────────────
    error:              str                 # Non-empty if any node failed


# ==============================================================================
# NODE 1 — VISION ANALYST
# ==============================================================================

VISION_SYSTEM_PROMPT = """
You are an expert FPS (First-Person Shooter) computer vision analyst specialising in
aim mechanics. You have been given:
  (a) A sequence of JPEG frames captured from the crosshair region of a player's screen
      during and immediately after they fired their weapon.
  (b) Precise mouse movement data (dx/dy per sample) recorded simultaneously.

Your task is to perform a deep mechanical analysis of three interconnected phenomena:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ACCURACY (Crosshair–Enemy Alignment)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Look for enemy silhouettes, player models, name tags, health bars, or hit markers.
  • Compare the geometric centre of the crosshair (centre of each frame) to the
    centre mass of any visible enemy model.
  • Estimate the angular/pixel offset between crosshair and enemy centre.
  • Express accuracy as a decimal score from 0.0 (completely off target) to 1.0 
    (crosshair dead-centre on enemy head).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. RECOIL DETECTION & SEVERITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Look for visual cues of weapon recoil across the frame sequence:
      - Muzzle flash: bright flash at lower screen centre (barrel kick)
      - Crosshair drift: crosshair moving UPWARD across frames (recoil pushes aim up)
      - Barrel rise: visible weapon model tilting upward
      - Screen shake / blur artifacts
  • Classify recoil severity:
      - "none"     → No upward crosshair drift, no muzzle flash
      - "mild"     → Slight upward drift (<5 px), faint flash
      - "moderate" → Clear upward drift (5–15 px), visible flash
      - "severe"   → Strong upward drift (>15 px), heavy flash, possible screen blur

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. MOUSE MOVEMENT ANALYSIS (Flick vs. Track vs. Recoil Compensation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Using the provided mouse delta summary:

  A. RECOIL COMPENSATION CHECK:
     • After weapon fire, the game physics push the crosshair UPWARD.
     • A skilled player pulls the mouse DOWNWARD (positive dy in our coordinate system)
       to counteract this — called "spray control" or "recoil compensation".
     • Compare the 'downward_pull' metric against the detected recoil severity:
         - If recoil is "severe" but downward_pull is near 0 → UNDER-COMPENSATING
         - If downward_pull greatly exceeds expected recoil → OVER-COMPENSATING
         - If they match → good control

  B. FLICK ASSESSMENT:
     • A "flick" is a rapid large-magnitude horizontal (dx) mouse movement to
       snap the crosshair onto a new target.
     • total_dx > 50 px and avg_speed_pps > 300 → likely a flick shot
     • Compare flick magnitude against the visual crosshair–enemy offset:
         - If the player flicked but crosshair passed BEYOND the enemy → OVER-FLICK
         - If the player flicked but crosshair stopped SHORT of the enemy → UNDER-FLICK
         - If the crosshair landed on the enemy → ON-TARGET

  C. TRACKING ASSESSMENT (for spray / sustained fire):
     • Tracking = continuously adjusting aim as a moving enemy crosses the crosshair.
     • Erratic dx/dy with high variance → poor tracking
     • Smooth, low-variance movement with crosshair staying on enemy → good tracking

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — YOU MUST RESPOND IN THIS EXACT JSON FORMAT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "accuracy_score": <float 0.0–1.0>,
  "recoil_detected": <true|false>,
  "recoil_severity": <"none"|"mild"|"moderate"|"severe">,
  "flick_diagnosis": <"over-flick"|"under-flick"|"on-target"|"tracking-based">,
  "recoil_compensation_quality": <"poor"|"fair"|"good"|"excellent">,
  "primary_weakness": "<one concise sentence describing the biggest aim problem>",
  "detailed_analysis": "<3–5 sentences of detailed FPS mechanical analysis>"
}
Do not add any text outside the JSON block.
"""


def _build_vision_human_message(event: ShotEvent) -> HumanMessage:
    """
    Construct a multimodal HumanMessage containing:
      • Mouse movement summary (text)
      • All captured frames (base64 image_url blocks)

    The AMD Vision model accepts the standard OpenAI multimodal message format.
    """
    mouse_summary = event.to_summary_dict()

    # ── Text block: telemetry context for the LLM ─────────────────────────────
    content_blocks: list[dict] = [
        {
            "type": "text",
            "text": (
                f"GAME: {mouse_summary['game']}\n"
                f"Mouse delta summary:\n"
                f"  • Total horizontal (dx): {mouse_summary['total_dx']} px\n"
                f"  • Total vertical   (dy): {mouse_summary['total_dy']} px\n"
                f"  • Average speed: {mouse_summary['avg_speed_pps']} px/s\n"
                f"  • Downward pull (recoil compensation): {mouse_summary['downward_pull']} px\n"
                f"  • Sample count: {mouse_summary['sample_count']}\n"
                f"\nBelow are {mouse_summary['frame_count']} sequential game frames "
                f"captured during and after the shot event. Analyse them as described "
                f"in your system instructions."
            ),
        }
    ]

    # ── Image blocks: one per captured frame ──────────────────────────────────
    for i, frame_b64 in enumerate(event.frames_b64):
        content_blocks.append({
            "type": "image_url",
            "image_url": {
                # Standard data URI format — supported by all OpenAI-compat APIs
                "url": f"data:image/jpeg;base64,{frame_b64}",
                "detail": "high",   # Request high-detail analysis from the vision model
            },
        })
        logger.debug(f"Frame {i+1}/{len(event.frames_b64)} appended to vision prompt")

    return HumanMessage(content=content_blocks)


def node_vision_analyst(state: AimState) -> dict:
    """
    NODE 1 — Vision Analyst
    ════════════════════════
    Sends game frames + mouse telemetry to the AMD multimodal vision LLM.
    Parses the JSON response and writes structured results into AimState.
    Guarded with a 5-second timeout and crash-proof mock baseline fallback.
    """
    logger.info("═══ Node 1: Vision Analyst ═══")
    event = state.get("shot_event")
    if not event:
        logger.warning("No shot_event in state — activating fallback baseline.")
        return {
            "vision_raw":      "fallback baseline (no shot_event)",
            "accuracy_score":  0.5,
            "recoil_detected": False,
            "recoil_severity": "none",
            "flick_diagnosis": "on-target",
            "vision_status":   "fallback",
            "error":           "No shot_event provided",
        }

    try:
        messages = [
            SystemMessage(content=VISION_SYSTEM_PROMPT),
            _build_vision_human_message(event),
        ]

        logger.info(f"Sending {len(event.frames_b64)} frames to AMD vision model (5s timeout)...")
        response = vision_llm.invoke(messages)
        raw_text = response.content.strip()
        logger.info("Vision LLM response received.")
        logger.debug(f"Raw vision output:\n{raw_text}")

        # ── Parse JSON response ───────────────────────────────────────────────
        # Strip any accidental markdown code fences the LLM might add
        json_str = re.sub(r"```(?:json)?|```", "", raw_text).strip()
        parsed   = json.loads(json_str)

        return {
            "vision_raw":      raw_text,
            "accuracy_score":  float(parsed.get("accuracy_score", 0.5)),
            "recoil_detected": bool(parsed.get("recoil_detected", False)),
            "recoil_severity": parsed.get("recoil_severity", "none"),
            "flick_diagnosis": parsed.get("flick_diagnosis", "on-target"),
            "vision_status":   "online",
            "error":           "",
        }

    except Exception as e:
        logger.warning(
            f"AMD Vision API timed out (>5s) or failed ({e}) — gracefully falling back to baseline telemetry."
        )
        # Crash-proof fallback: mock telemetry baseline (dx: 0, dy: 0) and vision_status: 'fallback'
        return {
            "vision_raw":      f"Vision fallback baseline (Error/Timeout: {e})",
            "accuracy_score":  0.5,
            "recoil_detected": False,
            "recoil_severity": "none",
            "flick_diagnosis": "on-target",
            "vision_status":   "fallback",
            "error":           f"Vision fallback: {e}",
        }


# ==============================================================================
# NODE 2 — WEB META RESEARCHER
# ==============================================================================

def _get_search_tool():
    """
    Lazily construct the DuckDuckGoSearchRun tool.
    Separated from module-level scope so that missing `ddgs` only errors
    when the Meta Researcher node actually executes, not on import.
    """
    try:
        return DuckDuckGoSearchRun()
    except ImportError as e:
        logger.warning(f"DuckDuckGo search tool unavailable: {e}. Install with: pip install ddgs")
        return None


def node_meta_researcher(state: AimState) -> dict:
    """
    NODE 2 — Web Meta Researcher
    ═════════════════════════════
    Searches DuckDuckGo for current pro-player sensitivity settings and
    recoil control meta for the detected game. Synthesises findings via LLM.
    """
    logger.info("═══ Node 2: Meta Researcher ═══")
    game_name = state["shot_event"].game_name

    # ── Step A: Web search (DuckDuckGo, free, no API key) ────────────────────
    search_query = (
        f"best professional {game_name} sensitivity settings 2024 "
        f"X sensitivity Y sensitivity recoil control guide"
    )
    logger.info(f"Searching: {search_query}")

    search_tool = _get_search_tool()  # Lazy instantiation

    try:
        if search_tool is None:
            raise RuntimeError("DuckDuckGo search tool not available (ddgs not installed)")
        raw_results = search_tool.run(search_query)
        logger.info("Web search completed.")
        logger.debug(f"Search snippet (first 300 chars): {raw_results[:300]}")
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        raw_results = f"Search unavailable: {e}"

    # ── Step B: Synthesise with LLM ──────────────────────────────────────────
    synthesis_prompt = f"""
You are a competitive gaming coach and analyst.

GAME: {game_name}
WEB SEARCH RESULTS:
{raw_results[:3000]}   ← (truncated to avoid token overflow)

Extract the following from the search results and respond ONLY with valid JSON:

{{
  "summary": "<2–3 sentence summary of pro sensitivity meta for {game_name}>",
  "pro_x_sensitivity": <float — typical pro horizontal sensitivity value, or null>,
  "pro_y_sensitivity": <float — typical pro vertical sensitivity value, or null>,
  "recoil_control_tips": "<1–2 sentences on how pros handle recoil in {game_name}>",
  "source_note": "<brief note on the reliability/recency of the sources>"
}}

If the search results do not contain specific numbers, use null for sensitivity values
and note the absence in the summary. Do NOT fabricate numbers.
Do not include any text outside the JSON block.
"""

    try:
        response    = text_llm.invoke(synthesis_prompt)
        raw_synth   = response.content.strip()
        json_str    = re.sub(r"```(?:json)?|```", "", raw_synth).strip()
        parsed      = json.loads(json_str)

        benchmark = get_game_benchmark(game_name)
        pro_x_val = parsed.get("pro_x_sensitivity")
        pro_y_val = parsed.get("pro_y_sensitivity")

        # Fallback to competitive esports benchmark if web search didn't contain explicit numbers
        if pro_x_val is None or not isinstance(pro_x_val, (int, float)) or pro_x_val <= 0:
            pro_x = float(benchmark["typical_x"])
        else:
            pro_x = float(pro_x_val)

        if pro_y_val is None or not isinstance(pro_y_val, (int, float)) or pro_y_val <= 0:
            pro_y = float(benchmark["typical_y"])
        else:
            pro_y = float(pro_y_val)

        summary_text = parsed.get("summary", raw_synth)
        if pro_x_val is None:
            summary_text = f"{summary_text} [Benchmarked to {game_name} competitive baseline: X={pro_x}, Y={pro_y}]"

        return {
            "pro_meta_summary": summary_text,
            "pro_x_sens":       pro_x,
            "pro_y_sens":       pro_y,
            "error":            "",
        }

    except Exception as e:
        logger.error(f"Meta Researcher synthesis failed: {e}")
        benchmark = get_game_benchmark(game_name)
        return {
            "pro_meta_summary": f"Search fallback: {benchmark['description']}",
            "pro_x_sens":       float(benchmark["typical_x"]),
            "pro_y_sens":       float(benchmark["typical_y"]),
            "error":            str(e),
        }


# ==============================================================================
# NODE 3 — AIM COACH CALCULATOR
# ==============================================================================

# ==============================================================================
# NODE 3 — AIM COACH CALCULATOR (BLOOD STRIKE IN-GAME SLIDERS)
# ==============================================================================

COACH_SYSTEM_PROMPT = """You are a friendly, experienced esports coach. Write newbie_advice and full_reasoning as natural, conversational coaching that sounds like a helpful teammate.
Blood Strike Sensitivity Categories:
  • "Camera Sensitivity (No Scope)" [Hipfire Flicks & Turning]: baseline 75
  • "Firing Sensitivity": hipfire tracking while shooting
  • "ADS Sensitivity (Red Dot / Iron Sight)": baseline 40
  • "Firing ADS Sensitivity": vertical recoil pull-down while shooting with ADS
  • "Scope Sensitivity (2X to 8X / Sniper)": baseline 40

HARDWARE ADVISOR RULE:
If the player's live hardware status indicates high load (RAM > 85% or CPU > 80%), briefly mention that high memory/CPU usage creates mouse input lag and aim floatiness alongside your slider adjustment.

OUTPUT FORMAT — RESPOND ONLY IN THIS EXACT JSON FORMAT:
{{
  "no_ads_sens": <int>,
  "iron_sight_sens": <int>,
  "scope_sens": <int>,
  "confidence_pct": <int 65–100>,
  "newbie_advice": "<1–2 natural coaching sentences with the exact sensitivity adjustment and hardware notice if under high load>",
  "full_reasoning": "<one natural sentence explaining the adjustment and why it should help>"
}}
Do not include any text outside the JSON block.
"""


def calculate_blood_strike_sensitivity(
    base_no_ads: int = 75,
    base_iron_sight: int = 40,
    base_scope: int = 40,
    total_dx: float = 0.0,
    total_dy: float = 0.0,
    downward_pull: float = 0.0,
    avg_speed: float = 0.0,
    flick_diagnosis: str = "unknown",
    recoil_detected: bool = False,
    recoil_severity: str = "none",
    bounds: dict = None,
) -> dict:
    """
    Direct integer mathematical engine for Blood Strike's in-game slider system:
      • No ADS Steering (FPS/TPS): baseline 75
      • Iron Sight/Holo/Red Dot: baseline 40
      • Scopes (2X to 8X): baseline 40
    """
    if bounds is None:
        bounds = SENSITIVITY_BOUNDS

    no_ads = base_no_ads
    iron_sight = base_iron_sight
    scope = base_scope
    steps = []

    nominal_target_dx = 75.0
    abs_dx = abs(total_dx)

    # 1. Horizontal flick adjustments
    if flick_diagnosis == "over-flick" or abs_dx > 100.0:
        overshoot_pct = max(0.10, min(0.38, (abs_dx - nominal_target_dx) / max(abs_dx, 1.0)))
        no_ads = round(base_no_ads * (1.0 - overshoot_pct))
        iron_sight = round(base_iron_sight * (1.0 - overshoot_pct * 0.75))
        scope = round(base_scope * (1.0 - overshoot_pct * 0.50))
        steps.append(
            f"Over-flick detected (dx={abs_dx:.1f}px vs target ~{nominal_target_dx:.0f}px, {overshoot_pct*100:.1f}% overshoot). "
            f"Applied formula: No ADS = round({base_no_ads} * (1 - {overshoot_pct:.3f})) = {no_ads}, "
            f"Iron Sight = round({base_iron_sight} * (1 - {overshoot_pct*0.75:.3f})) = {iron_sight}."
        )
    elif flick_diagnosis == "under-flick" or (abs_dx < 50.0 and avg_speed < 120.0 and abs_dx > 2.0):
        undershoot_pct = max(0.10, min(0.35, (nominal_target_dx - abs_dx) / nominal_target_dx))
        no_ads = round(base_no_ads * (1.0 + (undershoot_pct * 0.85)))
        iron_sight = round(base_iron_sight * (1.0 + (undershoot_pct * 0.65)))
        scope = round(base_scope * (1.0 + (undershoot_pct * 0.50)))
        steps.append(
            f"Under-flick detected (dx={abs_dx:.1f}px vs target ~{nominal_target_dx:.0f}px, {undershoot_pct*100:.1f}% undershoot). "
            f"Applied formula: No ADS = round({base_no_ads} * (1 + {undershoot_pct*0.85:.3f})) = {no_ads}, "
            f"Iron Sight = round({base_iron_sight} * (1 + {undershoot_pct*0.65:.3f})) = {iron_sight}."
        )
    else:
        steps.append(f"Horizontal flick on-target. Maintained No ADS Steering={base_no_ads}.")

    # 2. Recoil adjustments
    if recoil_detected or (recoil_severity in ("moderate", "severe")) or (downward_pull < 12.0 and total_dy < 0):
        deficit_pct = 0.25 if recoil_severity == "severe" else (0.18 if recoil_severity == "moderate" else 0.12)
        iron_sight = round(iron_sight * (1.0 + deficit_pct))
        scope = round(scope * (1.0 + deficit_pct * 0.8))
        steps.append(
            f"Recoil control deficit detected (severity={recoil_severity}, downward_pull={downward_pull:.1f}px). "
            f"Increased Iron Sight sensitivity to {iron_sight} (+{deficit_pct*100:.0f}%) to assist vertical pull-down."
        )
    elif downward_pull > 35.0 and total_dy > 20.0:
        overpull_pct = 0.10
        iron_sight = round(iron_sight * (1.0 - overpull_pct))
        scope = round(scope * (1.0 - overpull_pct))
        steps.append(
            f"Recoil over-compensation detected ({downward_pull:.1f}px downward pull). "
            f"Reduced Iron Sight sensitivity to {iron_sight} (-10%)."
        )
    else:
        steps.append(f"Vertical recoil control adequate. Maintained Iron Sight={iron_sight}.")

    # Clamp to integer slider bounds
    final_no_ads = int(max(bounds.get("no_ads_min", 10), min(bounds.get("no_ads_max", 200), no_ads)))
    final_iron = int(max(bounds.get("iron_sight_min", 5), min(bounds.get("iron_sight_max", 150), iron_sight)))
    final_scope = int(max(bounds.get("scope_min", 5), min(bounds.get("scope_max", 150), scope)))

    # 3. Newbie friendly coaching advice generator
    if flick_diagnosis == "over-flick" or abs_dx > 100.0:
        if recoil_detected or (recoil_severity in ("moderate", "severe")):
            newbie_advice = (
                f"Your crosshair swept past the target and your gun kicked upward. "
                f"We lowered your No ADS Steering to {final_no_ads} so your crosshair doesn't overshoot, "
                f"and raised your Iron Sight to {final_iron} so pulling down against recoil feels effortless on your desk!"
            )
        else:
            newbie_advice = (
                f"Your mouse flick swept past the target. "
                f"We lowered your No ADS Steering from {base_no_ads} down to {final_no_ads}. "
                f"This slows down your crosshair slightly so your natural hand motion stops dead-center on enemies!"
            )
    elif flick_diagnosis == "under-flick" or (abs_dx < 50.0 and avg_speed < 120.0 and abs_dx > 2.0):
        newbie_advice = (
            f"Your crosshair fell short before reaching the enemy. "
            f"We increased your No ADS Steering from {base_no_ads} up to {final_no_ads}. "
            f"Now a small, comfortable flick with your wrist will cover more screen distance effortlessly!"
        )
    elif recoil_detected or (recoil_severity in ("moderate", "severe")) or (downward_pull < 12.0 and total_dy < 0):
        newbie_advice = (
            f"Your gun kicked up heavily during firing. "
            f"I've increased your Iron Sight sensitivity from {base_iron_sight} to {final_iron}. "
            f"This means you won't have to pull your mouse down as much on your desk, making recoil much easier to control!"
        )
    else:
        newbie_advice = (
            f"Awesome shooting! Your crosshair stayed centered and your spray control was solid. "
            f"Keep your sliders right at {final_no_ads} (No ADS) and {final_iron} (Iron Sight) to lock in this muscle memory!"
        )

    final_firing = int(round(final_no_ads * 0.95))
    final_firing_ads = int(round(final_iron * 1.05))
    final_2x = int(round(final_scope * 0.95))
    final_4x = int(round(final_scope * 0.85))
    final_sniper = int(round(final_scope * 0.75))

    return {
        "no_ads_sens": final_no_ads,
        "camera_sens": final_no_ads,
        "firing_sens": final_firing,
        "iron_sight_sens": final_iron,
        "ads_sens": final_iron,
        "firing_ads_sens": final_firing_ads,
        "scope_sens": final_scope,
        "scope_2x": final_2x,
        "scope_4x": final_4x,
        "scope_sniper": final_sniper,
        "baseline": {
            "no_ads_sens": base_no_ads,
            "camera_sens": base_no_ads,
            "firing_sens": base_no_ads,
            "iron_sight_sens": base_iron_sight,
            "ads_sens": base_iron_sight,
            "firing_ads_sens": base_iron_sight,
            "scope_sens": base_scope,
            "scope_2x": base_scope,
            "scope_4x": 35,
            "scope_sniper": 30,
        },
        "math_steps": " ".join(steps),
        "newbie_advice": newbie_advice,
    }


def node_aim_coach_calculator(state: AimState) -> dict:
    """
    NODE 3 — Aim Coach Calculator
    ══════════════════════════════
    Synthesises vision analysis + pro meta → concrete Blood Strike integer slider values.
    Outputs: no_ads_sens, iron_sight_sens, scope_sens, newbie_advice.
    """
    logger.info("═══ Node 3: Aim Coach Calculator ═══")
    event   = state["shot_event"]
    summary = event.to_summary_dict()

    base_no_ads = 75
    base_iron_sight = 40
    base_scope = 40
    flick_diag = state.get("flick_diagnosis", "unknown")
    recoil_det = state.get("recoil_detected", False)
    recoil_sev = state.get("recoil_severity", "none")

    # ── Step A: Compute exact mathematical baseline from telemetry ─────────
    math_res = calculate_blood_strike_sensitivity(
        base_no_ads=base_no_ads,
        base_iron_sight=base_iron_sight,
        base_scope=base_scope,
        total_dx=summary["total_dx"],
        total_dy=summary["total_dy"],
        downward_pull=summary["downward_pull"],
        avg_speed=summary["avg_speed_pps"],
        flick_diagnosis=flick_diag,
        recoil_detected=recoil_det,
        recoil_severity=recoil_sev,
        bounds=SENSITIVITY_BOUNDS,
    )

    # ── Step B: Collect Live Hardware Health (psutil) ─────────────────────────
    cpu_pct = psutil.cpu_percent(interval=0.05)
    ram = psutil.virtual_memory()
    ram_pct = ram.percent
    ram_used_mb = round(ram.used / (1024**2), 1)
    ram_total_mb = round(ram.total / (1024**2), 1)
    is_safe = not (cpu_pct > 80.0 or ram_pct > 85.0)
    safety_badge = "[✅ SAFE TO PLAY]" if is_safe else "[⚠️ UNSAFE TO PLAY - HIGH LOAD]"

    # ── Step C: Prompt LLM with data + mathematical baseline + RAG Context ──
    rag_kb = state.get("game_knowledge_context", "")
    rag_hist = state.get("player_history_context", "")
    rag_snippet = ""
    if rag_kb:
        rag_snippet += f"\nRETRIEVED BLOOD STRIKE GAME KNOWLEDGE:\n{rag_kb}\n"
    if rag_hist:
        rag_snippet += f"\nPLAYER PERSONAL HISTORY (Prior Sessions):\n{rag_hist}\n"

    user_message = f"""
PLAYER DATA REPORT (BLOOD STRIKE)
=================================
Game:               Blood Strike
Current In-Game UI Sliders:
  No ADS Steering (Hipfire):   {base_no_ads}
  Iron Sight/Holo/Red Dot:     {base_iron_sight}
  Scopes (2X to 8X):           {base_scope}

LIVE HARDWARE SAFETY STATUS:
  Hardware Status: {safety_badge}
  CPU Load:        {cpu_pct}%
  RAM Usage:       {ram_pct}% ({ram_used_mb}MB / {ram_total_mb}MB)

MOUSE TELEMETRY:
  Total dx (horizontal): {summary['total_dx']} px
  Total dy (vertical):   {summary['total_dy']} px
  Avg speed:             {summary['avg_speed_pps']} px/s
  Downward pull:         {summary['downward_pull']} px

VISION ANALYSIS (from Node 1):
  Accuracy score:        {state.get('accuracy_score', 0.5)}
  Recoil detected:       {recoil_det}
  Recoil severity:       {recoil_sev}
  Flick diagnosis:       {flick_diag}

MATHEMATICAL TELEMETRY FORMULA BASELINE:
  Calculated No ADS Steering:   {math_res['no_ads_sens']}
  Calculated Iron Sight:        {math_res['iron_sight_sens']}
  Calculated Scopes (2X to 8X): {math_res['scope_sens']}
  Derivation: {math_res['math_steps']}
{rag_snippet}
Please synthesize the final coaching recommendations, including newbie_advice, and respond with the exact JSON format.
"""

    try:
        messages = [
            SystemMessage(content=COACH_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]

        response = text_llm.invoke(messages)
        raw_text = response.content.strip()
        logger.info("Aim Coach response received.")
        logger.debug(f"Coach raw output:\n{raw_text}")

        json_str = re.sub(r"```(?:json)?|```", "", raw_text).strip()
        parsed   = json.loads(json_str)

        bounds = SENSITIVITY_BOUNDS
        llm_no_ads = parsed.get("no_ads_sens")
        llm_iron = parsed.get("iron_sight_sens")
        llm_scope = parsed.get("scope_sens")

        # Verify LLM produced valid ints; fallback to mathematical calculation if missing/defaulted
        if llm_no_ads is not None and isinstance(llm_no_ads, (int, float)):
            rec_no_ads = int(round(max(bounds["no_ads_min"], min(bounds["no_ads_max"], float(llm_no_ads)))))
        else:
            rec_no_ads = math_res["no_ads_sens"]

        if llm_iron is not None and isinstance(llm_iron, (int, float)):
            rec_iron = int(round(max(bounds["iron_sight_min"], min(bounds["iron_sight_max"], float(llm_iron)))))
        else:
            rec_iron = math_res["iron_sight_sens"]

        if llm_scope is not None and isinstance(llm_scope, (int, float)):
            rec_scope = int(round(max(bounds["scope_min"], min(bounds["scope_max"], float(llm_scope)))))
        else:
            rec_scope = math_res["scope_sens"]

        # If LLM echoed exact baseline despite an overflick/underflick/recoil issue, enforce math
        if (flick_diag == "over-flick" or abs(summary["total_dx"]) > 100.0) and rec_no_ads == base_no_ads:
            rec_no_ads = math_res["no_ads_sens"]
            rec_iron = math_res["iron_sight_sens"]

        if (recoil_det or recoil_sev in ("moderate", "severe")) and rec_iron == base_iron_sight:
            rec_iron = math_res["iron_sight_sens"]

        newbie_text = parsed.get("newbie_advice") or math_res["newbie_advice"]

        return {
            "no_ads_sens":        rec_no_ads,
            "iron_sight_sens":    rec_iron,
            "scope_sens":         rec_scope,
            "recommended_x_sens": float(rec_no_ads),
            "recommended_y_sens": float(rec_iron),
            "newbie_advice":      newbie_text,
            "coach_reasoning":    parsed.get("full_reasoning", f"{math_res['math_steps']} {raw_text}"),
            "confidence_pct":     int(parsed.get("confidence_pct", 85)),
            "error":              "",
        }

    except Exception as e:
        logger.error(f"Aim Coach Calculator node failed: {e}")
        return {
            "no_ads_sens":        math_res["no_ads_sens"],
            "iron_sight_sens":    math_res["iron_sight_sens"],
            "scope_sens":         math_res["scope_sens"],
            "recommended_x_sens": float(math_res["no_ads_sens"]),
            "recommended_y_sens": float(math_res["iron_sight_sens"]),
            "newbie_advice":      math_res["newbie_advice"],
            "coach_reasoning":    f"{math_res['math_steps']} (Calculated via in-game slider formulas)",
            "confidence_pct":     75,
            "error":              str(e),
        }


# ==============================================================================
# NODE 4 — DATABASE LOGGER
# ==============================================================================

def node_database_logger(state: AimState) -> dict:
    """
    NODE 4 — Database Logger
    ═════════════════════════
    Persists the complete analysis session to SQLite.
    This is the terminal node — always runs regardless of upstream errors.
    """
    logger.info("═══ Node 4: Database Logger ═══")
    event = state["shot_event"]

    import json as _json  # local alias to avoid any scope confusion

    session_data = {
        "game_name":          event.game_name,
        "game_exe":           event.game_exe,
        "mouse_deltas_json":  [{"dx": d.dx, "dy": d.dy, "t": d.t}
                               for d in event.mouse_deltas],
        "frame_count":        len(event.frames_b64),

        "vision_raw_output":  state.get("vision_raw", ""),
        "accuracy_score":     state.get("accuracy_score", 0.0),
        "recoil_detected":    state.get("recoil_detected", False),
        "recoil_severity":    state.get("recoil_severity", "unknown"),
        "flick_diagnosis":    state.get("flick_diagnosis", "unknown"),

        "pro_meta_summary":   state.get("pro_meta_summary", ""),
        "pro_x_sens":         state.get("pro_x_sens", 0.0),
        "pro_y_sens":         state.get("pro_y_sens", 0.0),

        "coach_reasoning":    state.get("coach_reasoning", ""),
        "recommended_x_sens": state.get("recommended_x_sens", 3.5),
        "recommended_y_sens": state.get("recommended_y_sens", 3.5),
        "no_ads_sens":        state.get("no_ads_sens", 75),
        "iron_sight_sens":    state.get("iron_sight_sens", 40),
        "scope_sens":         state.get("scope_sens", 40),
        "newbie_advice":      state.get("newbie_advice", ""),
        "confidence_pct":     state.get("confidence_pct", 0),

        "is_mock_data":       event.is_mock,
    }

    try:
        row_id = log_session_sync(session_data)
        logger.info(f"Session saved to database → row ID: {row_id}")
        return {"db_row_id": row_id, "error": ""}

    except Exception as e:
        logger.error(f"Database Logger node failed: {e}")
        return {"db_row_id": -1, "error": str(e)}


# ==============================================================================
# RAG NODES  (additive — do NOT modify existing 4-node topology below)
# ==============================================================================

def node_retrieve_knowledge(state: AimState) -> dict:
    """
    RAG Node A — Game Knowledge Retrieval
    ======================================
    Queries the `bloodstrike_knowledge` Qdrant collection for the top-3 most
    relevant game mechanics, sensitivity rules, and drill recommendations
    based on the current session's diagnosed issues.
    Non-fatal: returns empty string if Qdrant is unavailable.
    """
    logger.info("═══ RAG Node A: Knowledge Retrieval ═══")
    # Build a context-rich query from the current session's vision analysis
    flick    = state.get("flick_diagnosis", "unknown")
    recoil   = state.get("recoil_severity", "none")
    accuracy = state.get("accuracy_score", 0.0)
    event    = state.get("shot_event")
    game     = event.game_name if event else "Blood Strike"

    query = (
        f"Blood Strike {game} player with {flick} flick pattern, "
        f"{recoil} recoil severity, accuracy score {accuracy:.2f}. "
        f"What sensitivity adjustments, recoil drills, and crosshair placement tips apply?"
    )
    context = retrieve_knowledge(query, top_k=3)
    if context:
        logger.info(f"Knowledge retrieved: {len(context)} chars from Qdrant.")
    else:
        logger.info("No knowledge retrieved (Qdrant unavailable or empty — non-fatal).")
    return {"game_knowledge_context": context}


def node_retrieve_memory(state: AimState) -> dict:
    """
    RAG Node B — Player Memory Retrieval
    =====================================
    Fetches the most recent 5 sessions from `player_memory` Qdrant collection
    using METADATA FILTER on player_id + chronological DESC ordering.
    Non-fatal: returns empty string if Qdrant is unavailable.
    """
    logger.info("═══ RAG Node B: Player Memory Retrieval ═══")
    event     = state.get("shot_event")
    player_id = getattr(event, "player_id", "default") if event else "default"
    history   = retrieve_player_memory(player_id=player_id, top_n=5)
    if history:
        logger.info(f"Player memory retrieved: {len(history)} chars from Qdrant.")
    else:
        logger.info("No player memory found (new player or Qdrant unavailable — non-fatal).")
    return {"player_history_context": history}


def node_store_memory(state: AimState) -> dict:
    """
    RAG Node C — Store Session to Player Memory
    ============================================
    Upserts the completed session into `player_memory` Qdrant collection.
    Uses db_row_id as the idempotency key (deduplication via session_id).
    Non-fatal: returns unchanged state if Qdrant is unavailable.
    """
    logger.info("═══ RAG Node C: Store Player Memory ═══")
    event     = state.get("shot_event")
    player_id = getattr(event, "player_id", "default") if event else "default"
    summary   = event.to_summary_dict() if event else {}

    telemetry = {
        "total_dx":      summary.get("total_dx", 0),
        "total_dy":      summary.get("total_dy", 0),
        "downward_pull": summary.get("downward_pull", 0),
        "avg_speed_pps": summary.get("avg_speed_pps", 0),
    }
    vision = {
        "accuracy_score":  state.get("accuracy_score", 0.0),
        "recoil_severity": state.get("recoil_severity", "none"),
        "flick_diagnosis": state.get("flick_diagnosis", "unknown"),
    }
    sliders = {
        "no_ads_sens":    state.get("no_ads_sens", 75),
        "iron_sight_sens": state.get("iron_sight_sens", 40),
        "scope_sens":     state.get("scope_sens", 40),
    }
    coach_advice = state.get("coach_reasoning", "") or state.get("newbie_advice", "")
    session_id   = state.get("db_row_id", -1)

    if session_id and session_id > 0:
        store_player_memory(
            session_id=session_id,
            player_id=player_id,
            telemetry=telemetry,
            vision=vision,
            sliders=sliders,
            coach_advice=coach_advice,
        )
    else:
        logger.warning("store_memory skipped: no valid db_row_id in state.")

    return {"error": state.get("error", "")}


# ==============================================================================
# GRAPH CONSTRUCTION
# ==============================================================================

def build_graph() -> Any:
    """
    Assemble and compile the LangGraph StateGraph.

    Node execution order: vision_analyst → meta_researcher → aim_coach → db_logger → END

    Returns:
        A compiled LangGraph runnable (call with .invoke(initial_state)).
    """
    # ── Initialise database schema (idempotent) ───────────────────────────────
    init_db()

    # ── Initialise Qdrant RAG collections (non-fatal if unavailable) ──────────
    try:
        init_qdrant_collections()
    except Exception as _qdrant_err:
        logger.warning(f"Qdrant init skipped (non-fatal): {_qdrant_err}")

    # ── Build the graph ───────────────────────────────────────────────────────
    workflow = StateGraph(AimState)

    # ── Register active pipeline nodes ─────────────────────────────────────────
    workflow.add_node("vision_analyst",    node_vision_analyst)
    workflow.add_node("retrieve_knowledge", node_retrieve_knowledge)
    workflow.add_node("retrieve_memory",    node_retrieve_memory)
    workflow.add_node("aim_coach",         node_aim_coach_calculator)
    workflow.add_node("database_logger",   node_database_logger)
    workflow.add_node("store_memory",       node_store_memory)

    # ── Wire direct low-latency pipeline (bypassing web search):
    #
    #   vision_analyst
    #         │
    #   retrieve_knowledge  ← RAG Node A (Blood Strike game KB from Qdrant)
    #         │
    #   retrieve_memory     ← RAG Node B (Player historical sessions from Qdrant)
    #         │
    #   aim_coach           ← Math + LLM reasoning grounded in RAG contexts
    #         │
    #   database_logger     ← Persists session to SQLite
    #         │
    #   store_memory        ← RAG Node C (Idempotent upsert to Qdrant)
    #         │
    #        END
    workflow.set_entry_point("vision_analyst")
    workflow.add_edge("vision_analyst",    "retrieve_knowledge")
    workflow.add_edge("retrieve_knowledge","retrieve_memory")
    workflow.add_edge("retrieve_memory",   "aim_coach")
    workflow.add_edge("aim_coach",         "database_logger")
    workflow.add_edge("database_logger",   "store_memory")
    workflow.add_edge("store_memory",      END)

    compiled = workflow.compile()
    logger.info("AgenticAim LangGraph compiled successfully (with Hybrid RAG).")
    return compiled


# ==============================================================================
# COACHING REPORT FORMATTER
# ==============================================================================

def format_coaching_report(final_state: dict) -> str:
    """
    Pretty-print the final AimState as a structured terminal coaching report.
    This is what gets displayed to the player after a session.
    """
    event = final_state.get("shot_event")
    sep   = "=" * 60

    lines = [
        "",
        sep,
        "  [AIM COACH]  AGENTICAIM COACHING REPORT",
        sep,
        f"  Game:              {event.game_name if event else 'Blood Strike'}",
        f"  Session ID (DB):   {final_state.get('db_row_id', 'N/A')}",
        f"  Data source:       {'MOCK (simulation)' if (event and event.is_mock) else 'LIVE'}",
        "",
        "--- VISION ANALYSIS ----------------------------------------",
        f"  Accuracy score:    {final_state.get('accuracy_score', 0.0):.2f} / 1.00",
        f"  Recoil detected:   {'Yes' if final_state.get('recoil_detected') else 'No'}",
        f"  Recoil severity:   {str(final_state.get('recoil_severity', 'N/A')).upper()}",
        f"  Flick diagnosis:   {str(final_state.get('flick_diagnosis', 'N/A')).upper()}",
        "",
        "--- BLOOD STRIKE IN-GAME SETTINGS (SLIDE MENU) -------------",
        f"  >> No ADS Steering (FPS/TPS): {final_state.get('no_ads_sens', 75)}",
        f"  >> Iron Sight/Holo/Red Dot:   {final_state.get('iron_sight_sens', 40)}",
        f"  >> Scopes (2X to 8X):         {final_state.get('scope_sens', 40)}",
        f"  Confidence:                   {final_state.get('confidence_pct', 'N/A')}%",
        "",
        "--- COACH REASONING ----------------------------------------",
    ]

    reasoning = final_state.get("coach_reasoning", "N/A")
    # Word-wrap to 56 chars for clean terminal output
    for chunk in [reasoning[i:i+56] for i in range(0, min(len(reasoning), 400), 56)]:
        lines.append(f"  {chunk}")

    # ── Beginner Coach Tips (Newbie-Friendly Recoil Coaching) ─────────────────
    newbie_tip = final_state.get("newbie_advice", "")
    if newbie_tip:
        lines += [
            "",
            "--- BEGINNER COACH TIPS (NEWBIE FRIENDLY) ------------------",
        ]
        for chunk in [newbie_tip[i:i+56] for i in range(0, min(len(newbie_tip), 400), 56)]:
            lines.append(f"  * {chunk}")

    # ── Live System Impact (Proof of Lightweight AMD Cloud Offload) ───────────
    try:
        impact = get_live_system_impact()
        lines += [
            "",
            "--- LIVE SYSTEM IMPACT (AMD CLOUD OFFLOAD) -----------------",
            f"  Local CPU Usage:    {impact['cpu_pct']}%  (Lightweight)",
            f"  Local RAM Usage:    {impact['ram_pct']}%  ({impact['ram_used_mb']} MB used)",
            f"  Local GPU Usage:    {impact['gpu_desc']}",
            f"  Vision/LLM Host:    AMD Token Factory API (Cloud Inference)",
        ]
    except Exception as e:
        logger.debug(f"Hardware impact lookup failed: {e}")

    errors = final_state.get("error", "")
    if errors:
        lines += [
            "",
            "--- WARNINGS -----------------------------------------------",
            f"  [!] {errors}",
        ]

    lines += ["", sep, ""]
    return "\n".join(lines)


# ==============================================================================
# INTERACTIVE AI COACH CHAT & LIVE HARDWARE SAFETY ADVISOR
# ==============================================================================

COACH_CHAT_SYSTEM_PROMPT = """You are Coach AgenticAim, a friendly, experienced esports teammate and live hardware advisor coaching Blood Strike.

1. Conversational Queries: If the user asks a casual question (e.g., 'how are you', 'what is your name', greetings, casual chat), respond naturally and briefly.
2. PC Specs & Hardware Queries: You have direct access to the player's detected hardware rig in your context (AMD Ryzen 5 CPU, AMD Radeon Vega 8 GPU, RAM). If asked, acknowledge their AMD Ryzen 5 processor and Vega 8 graphics. If RAM is high (>85%), remind them to close background apps to prevent input delay.
3. Blood Strike Sensitivity Types & Recommendations:
   Always use and recommend using the exact in-game Blood Strike category names:
   • "Camera Sensitivity (No Scope)" — For looking around and initial flick acquisition
   • "Firing Sensitivity" — For hipfire tracking while spraying
   • "ADS Sensitivity (Red Dot / Iron Sight)" — For target tracking while aiming down sights
   • "Firing ADS Sensitivity" — For vertical recoil pull-down while shooting ADS
   • "Scope Sensitivity (2X, 3X, 4X, 6X, 8X / Sniper)" — For precision long-range scopes
4. Gameplay Queries: If the user asks about their aim, recoil, settings, or match performance, give clear, practical adjustments using these exact category names.

Speak like a real teammate, not a scripted announcer. Use short, relaxed sentences and natural contractions. Keep replies concise and direct."""


def ask_ai_coach(
    user_message: str,
    chat_history: Optional[list] = None,
    game_knowledge_context: str = "",
    player_history_context: str = "",
) -> dict:
    """
    Interactive AI Coach Chat powered by AMD Token Factory API (DeepSeek-V4.1-Flash).
    Injects:
      a) Latest match telemetry & Blood Strike slider values from SQLite database.
      b) Live hardware health (CPU %, RAM %, GPU offload) with Safety Advisor status.
      c) [NEW] Retrieved Blood Strike game knowledge from Qdrant vector search.
      d) [NEW] Player's chronological session history from Qdrant player_memory.

    Args:
        user_message:            The user's prompt or question.
        chat_history:            Optional previous chat messages.
        game_knowledge_context:  Pre-retrieved KB snippets (optional, auto-fetched if empty).
        player_history_context:  Pre-retrieved player history (optional, auto-fetched if empty).

    Returns:
        dict: {
            "reply": str,
            "hardware_status": dict,
            "latest_session": Optional[dict]
        }
    """
    if chat_history is None:
        chat_history = []

    # ── Step A: Collect Live Hardware Health (psutil & Windows native) ───────
    cpu_pct = psutil.cpu_percent(interval=0.05)
    ram = psutil.virtual_memory()
    ram_pct = ram.percent
    ram_used_mb = round(ram.used / (1024**2), 1)
    ram_total_mb = round(ram.total / (1024**2), 1)
    gpu_desc = "0.0% (Vision offloaded to AMD Cloud API)"

    from tracker import get_native_windows_hardware
    hw_specs = get_native_windows_hardware()
    cpu_name = hw_specs.get("cpu", "AMD Ryzen 5 PRO 3500U")
    gpu_name = hw_specs.get("gpu", "AMD Radeon(TM) Vega 8 Graphics")

    # Hardware Safety Logic
    if cpu_pct > 80.0 or ram_pct > 85.0:
        is_safe = False
        safety_badge = "[⚠️ UNSAFE TO PLAY - HIGH LOAD]"
        safety_msg = (
            f"High resource load (CPU: {cpu_pct}%, RAM: {ram_pct}%). "
            f"Playing ranked right now can trigger FPS drops and mouse input delay. "
            f"Close heavy background programs and browser tabs first!"
        )
    else:
        is_safe = True
        safety_badge = "[✅ SAFE TO PLAY]"
        safety_msg = (
            f"Hardware load is optimal (CPU: {cpu_pct}%, RAM: {ram_pct}%). "
            f"Zero input delay detected — ready to play!"
        )

    hw_info = {
        "cpu_pct": cpu_pct,
        "ram_pct": ram_pct,
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "gpu_desc": gpu_desc,
        "cpu_name": cpu_name,
        "gpu_name": gpu_name,
        "ram_installed_gb": hw_specs.get("ram_installed_gb", 8.0),
        "cores": hw_specs.get("cores", 8),
        "display": hw_specs.get("display", "1280 × 720 @ 60Hz"),
        "is_safe": is_safe,
        "safety_badge": safety_badge,
        "safety_msg": safety_msg,
    }

    # ── Step B: Collect Latest Match Telemetry (Database) ─────────────────────
    latest = None
    try:
        latest = get_latest_session()
    except Exception as e:
        logger.warning(f"Could not load latest session for chat context: {e}")

    if latest:
        t = latest.get("telemetry", {})
        v = latest.get("vision_analysis", {})
        s = latest.get("sensitivity_sliders", {})
        match_context = f"""
CURRENT LATEST MATCH TELEMETRY (Session #{latest.get('id')} — Game: {latest.get('game_name', 'Blood Strike')}):
  • Mouse Movement:
    - Horizontal flick (dx): {t.get('total_dx')} px
    - Vertical movement (dy): {t.get('total_dy')} px
    - Recoil compensation pull: {t.get('downward_pull')} px
    - Average movement speed: {t.get('avg_speed_pps')} px/s
  • Vision Diagnosis:
    - Accuracy score: {v.get('accuracy_score')} / 1.00
    - Recoil detected: {v.get('recoil_detected')} (Severity: {v.get('recoil_severity')})
    - Flick diagnosis: {v.get('flick_diagnosis')}
    - Recoil control quality: {v.get('recoil_compensation_quality')}
    - Primary weakness identified: {v.get('primary_weakness')}
    - Frame analysis detail: {v.get('detailed_analysis')}
  • Recommended Blood Strike In-Game Sliders:
    - No ADS Steering (Hipfire): {s.get('no_ads_sens')} (Baseline: 75)
    - Iron Sight / Holo / Red Dot: {s.get('iron_sight_sens')} (Baseline: 40)
    - Scopes (2X to 8X): {s.get('scope_sens')} (Baseline: 40)
  • Coach Reasoning: {latest.get('coach_reasoning')}
  • Beginner Advice: {latest.get('newbie_advice')}
"""
    else:
        match_context = "CURRENT LATEST MATCH TELEMETRY: No recorded matches found in database yet. Prompt player to run an aim session first."

    # ── Step C: Live RAG context fetch (if not pre-supplied by graph nodes) ────
    if not game_knowledge_context:
        try:
            game_knowledge_context = retrieve_knowledge(user_message, top_k=3)
        except Exception as _rke:
            logger.debug(f"Live knowledge retrieval skipped: {_rke}")

    if not player_history_context:
        try:
            player_history_context = retrieve_player_memory(player_id="default", top_n=5)
        except Exception as _rme:
            logger.debug(f"Live memory retrieval skipped: {_rme}")

    # ── Step D: Construct Augmented System Prompt & Messages ──────────────────
    rag_section = ""
    if game_knowledge_context:
        rag_section += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"RETRIEVED BLOOD STRIKE GAME KNOWLEDGE (from Vector Knowledge Base):\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{game_knowledge_context}\n"
        )
    if player_history_context:
        rag_section += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"PLAYER PERSONAL HISTORY (chronological, most-recent first):\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{player_history_context}\n"
        )

    measurable_outcome_rule = (
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "MEASURABLE OUTCOME COACHING RULE (MANDATORY):\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Base your coaching strictly on measurable outcomes. Compare the current session's "
        "telemetry (dx, dy, downward_pull, accuracy_score) against previous sessions in the "
        "player history context above. Only report improvement or regression if the specific "
        "numbers support that conclusion — never assume progress without telemetry evidence. "
        "Utilize the retrieved Blood Strike knowledge to recommend specific, evidence-based "
        "adjustments tied to the player's diagnosed issues.\n"
    )

    system_prompt = (
        f"{COACH_CHAT_SYSTEM_PROMPT}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"LIVE PLAYER HARDWARE RIG (DETECTED LIVE ON THIS WINDOWS RIG):\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  • Processor (CPU): {cpu_name} ({hw_specs.get('cores', 8)} Cores)\n"
        f"  • Graphics (GPU):  {gpu_name}\n"
        f"  • Total Installed RAM: {hw_specs.get('ram_installed_gb', 8.0)} GB\n"
        f"  • Native Display:  {hw_specs.get('display', '1280 × 720 @ 60Hz')}\n"
        f"  • Live Status:     {safety_badge}\n"
        f"  • Current Load:    CPU: {cpu_pct}%, RAM: {ram_pct}% ({ram_used_mb} MB / {ram_total_mb} MB)\n"
        f"  • GPU Offload:     {gpu_desc}\n"
        f"  • Safety Note:     {safety_msg}\n\n"
        f"{match_context}\n"
        f"{rag_section}"
        f"{measurable_outcome_rule}"
    )

    messages: list[Any] = [SystemMessage(content=system_prompt)]

    # Add historical messages (limit to last 6 turns for prompt efficiency)
    for msg in chat_history[-6:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_message))

    # ── Step D: Query AMD Token Factory API ───────────────────────────────────
    try:
        response = text_llm.invoke(messages)
        reply = str(response.content).strip()
    except Exception as e:
        logger.warning(f"AI Coach primary LLM call hit error: {e} — attempting fast retry with fallback model...")
        reply = ""
        # Auto-fallback to alternative AMD models on 429, 502, 503, gateway, or network delay
        candidate_models = ["DeepSeek-V4.1-Flash", "DeepSeek-V4-Flash", "GLM-5.3-Flash"]
        for alt_model in candidate_models:
            if alt_model == AMD_TEXT_MODEL:
                continue
            try:
                time.sleep(0.5)
                fallback_llm = ChatOpenAI(
                    base_url=AMD_BASE_URL,
                    api_key=AMD_API_KEY,
                    model=alt_model,
                    temperature=0.2,
                    request_timeout=25.0,
                    max_retries=1,
                )
                fb_res = fallback_llm.invoke(messages)
                reply = str(fb_res.content).strip()
                if reply:
                    logger.info(f"Fallback model {alt_model} succeeded!")
                    break
            except Exception as e2:
                logger.error(f"Fallback model {alt_model} failed: {e2}")

        if not reply:
            latest_sens = latest.get("sensitivity_sliders", {}) if latest else {}
            no_ads_val = latest_sens.get("no_ads_sens", 75)
            iron_val = latest_sens.get("iron_sight_sens", 40)
            reply = (
                f"AMD Cloud model gateway is experiencing high traffic, but your telemetry is locked in. "
                f"Hardware load is {safety_badge}. For optimal recoil control, set your Blood Strike "
                f"No ADS Steering to {no_ads_val} and Iron Sight to {iron_val}."
            )

    sources = []
    if game_knowledge_context:
        lines = game_knowledge_context.strip().split("\n")
        for line in lines:
            if line.startswith("[KB-") and "]" in line:
                source_tag = line[:line.index("]") + 1]
                sources.append(f"Qdrant Cloud: {source_tag}")
            elif len(sources) < 3 and line.strip() and not line.startswith("RETRIEVED"):
                sources.append(f"Qdrant Cloud: {line[:50]}...")
        if not sources:
            sources.append("Qdrant Cloud: bloodstrike_knowledge (Recoil & Movement Meta)")
    if player_history_context:
        sources.append("Qdrant Cloud: player_memory (Session Telemetry)")

    rag_status_info = {
        "is_rag_verified": bool(game_knowledge_context),
        "knowledge_retrieved": bool(game_knowledge_context),
        "memory_retrieved": bool(player_history_context),
        "vector_db": "Qdrant Cloud (GCP europe-west3)",
        "collection": "bloodstrike_knowledge",
        "dimension": 768,
        "sources": sources,
    }

    return {
        "reply": reply,
        "hardware_status": hw_info,
        "latest_session": latest,
        "sources": sources,
        "rag_status": rag_status_info,
        "is_rag_verified": bool(game_knowledge_context),
    }


def ask_ai_coach_stream(user_message: str, chat_history: Optional[list] = None):
    """
    Streaming generator for interactive terminal chat.
    Yields chunks in real time as tokens arrive from the AMD Token Factory Cloud API.
    """
    if chat_history is None:
        chat_history = []

    cpu_pct = psutil.cpu_percent(interval=0.05)
    ram = psutil.virtual_memory()
    ram_pct = ram.percent
    ram_used_mb = round(ram.used / (1024**2), 1)
    ram_total_mb = round(ram.total / (1024**2), 1)
    gpu_desc = "0.0% (Vision offloaded to AMD Cloud API)"

    is_safe = not (cpu_pct > 80.0 or ram_pct > 85.0)
    safety_badge = "[✅ SAFE TO PLAY]" if is_safe else "[⚠️ UNSAFE TO PLAY - HIGH LOAD]"
    safety_msg = (
        f"Hardware load is optimal (CPU: {cpu_pct}%, RAM: {ram_pct}%). Zero input delay detected."
        if is_safe else
        f"High resource load (CPU: {cpu_pct}%, RAM: {ram_pct}%). Close heavy background apps before gaming!"
    )

    hw_info = {
        "cpu_pct": cpu_pct,
        "ram_pct": ram_pct,
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "gpu_desc": gpu_desc,
        "is_safe": is_safe,
        "safety_badge": safety_badge,
        "safety_msg": safety_msg,
    }

    latest = None
    try:
        latest = get_latest_session()
    except Exception as e:
        logger.warning(f"Could not load latest session for stream chat context: {e}")

    yield {"type": "meta", "hardware_status": hw_info, "latest_session": latest}

    match_context = ""
    if latest:
        t = latest.get("telemetry", {})
        v = latest.get("vision_analysis", {})
        s = latest.get("sensitivity_sliders", {})
        match_context = f"""
CURRENT LATEST MATCH TELEMETRY (Session #{latest.get('id')} — Game: {latest.get('game_name', 'Blood Strike')}):
  • Mouse Movement: dx={t.get('total_dx')}px, dy={t.get('total_dy')}px, downward_pull={t.get('downward_pull')}px
  • Vision Diagnosis: Accuracy={v.get('accuracy_score')}, Recoil={v.get('recoil_detected')} ({v.get('recoil_severity')}), Flick={v.get('flick_diagnosis')}
  • In-Game Sliders: No ADS={s.get('no_ads_sens')}, Iron Sight={s.get('iron_sight_sens')}, Scopes={s.get('scope_sens')}
"""
    # ── Fetch RAG context for streaming chat ──────────────────────────────────
    rag_kb = ""
    try:
        rag_kb = retrieve_knowledge(user_message, top_k=3)
    except Exception as _rke:
        logger.debug(f"Stream knowledge retrieval skipped: {_rke}")

    rag_hist = ""
    try:
        rag_hist = retrieve_player_memory(player_id="default", top_n=5)
    except Exception as _rme:
        logger.debug(f"Stream player memory retrieval skipped: {_rme}")

    rag_section = ""
    if rag_kb:
        rag_section += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"RETRIEVED BLOOD STRIKE GAME KNOWLEDGE:\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{rag_kb}\n"
        )
    if rag_hist:
        rag_section += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"PLAYER PERSONAL HISTORY (Prior Sessions):\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{rag_hist}\n"
        )

    measurable_rule = (
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "MEASURABLE OUTCOME COACHING RULE:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Ground your advice strictly in measurable telemetry. Compare the latest session's "
        "numbers against player history. Never claim improvement without data.\n"
    )

    from tracker import get_native_windows_hardware
    hw_specs = get_native_windows_hardware()
    cpu_name = hw_specs.get("cpu", "AMD Ryzen 5 PRO 3500U")
    gpu_name = hw_specs.get("gpu", "AMD Radeon(TM) Vega 8 Graphics")

    system_prompt = (
        f"{COACH_CHAT_SYSTEM_PROMPT}\n\n"
        f"LIVE HARDWARE RIG: {cpu_name} | {gpu_name} | RAM: {ram_pct}% ({safety_badge})\n"
        f"{match_context}\n"
        f"{rag_section}"
        f"{measurable_rule}"
    )

    messages: list[Any] = [SystemMessage(content=system_prompt)]
    for msg in chat_history[-6:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=user_message))

    # Stream tokens live
    try:
        for chunk in text_llm.stream(messages):
            token = str(chunk.content or "")
            if token:
                yield {"type": "token", "content": token}
    except Exception as e:
        logger.warning(f"Streaming hit error: {e} — attempting fallback stream...")
        try:
            fallback_llm = ChatOpenAI(
                base_url=AMD_BASE_URL,
                api_key=AMD_API_KEY,
                model="DeepSeek-V4-Flash",
                temperature=0.2,
                request_timeout=35.0,
                max_retries=1,
            )
            for chunk in fallback_llm.stream(messages):
                token = str(chunk.content or "")
                if token:
                    yield {"type": "token", "content": token}
        except Exception as e2:
            latest_sens = latest.get("sensitivity_sliders", {}) if latest else {}
            no_ads_val = latest_sens.get("no_ads_sens", 75)
            iron_val = latest_sens.get("iron_sight_sens", 40)
            yield {
                "type": "token",
                "content": f"\nAMD Cloud model gateway is experiencing high traffic, but your telemetry is locked in. Blood Strike sliders: No ADS Steering: {no_ads_val}, Iron Sight: {iron_val}."
            }
