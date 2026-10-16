"""
config.py — AgenticAim Central Configuration
==============================================
Single source of truth for:
  • Game executable → display-name mappings (scalable for any new FPS title)
  • AMD Token Factory API credentials
  • Model selection (text + vision)
  • Sensitivity parameter bounds used by the coach calculator

AMD Developer Hackathon | AI-Powered Esports Aim Coach
"""

import os
from dotenv import load_dotenv

# Load any overrides from a local .env file (optional — values below are the defaults)
load_dotenv()

# ==============================================================================
# SECTION 1 — AMD Token Factory API Settings
# ==============================================================================

# The AMD Radeon Cloud Token Factory OpenAI-compatible endpoint.
AMD_BASE_URL: str = os.getenv(
    "AMD_BASE_URL",
    "https://developer.amd.com.cn/radeon/api/v1"
)

# Your personal AMD Token Factory API key.
# DO NOT commit the real key to source control — use a .env file in production.
AMD_API_KEY: str = os.getenv(
    "AMD_API_KEY",
    "rc-f395274bec7fb4894b9e4838dff18204088bf77200627225"
)

# ── Text / Reasoning Model ────────────────────────────────────────────────────
# Used for: Meta Researcher, Aim Coach Calculator, and Database Logger nodes.
#
# AVAILABLE AMD TEXT MODELS (verified live via /v1/models endpoint):
#   DeepSeek-V4.1-Flash     <- RECOMMENDED (latest, fast)
#   DeepSeek-V4-Flash       <- Stable alternative
#   Gemma-4-31B-IT          <- Google Gemma, larger
#   GLM-5.3-Flash           <- Zhipu AI flash
#   MiMo-V2.6-Flash         <- Xiaomi MiMo flash
#   Qwen3.8-27B             <- Larger Qwen
#   Qwen3.8-Flash-Next      <- Qwen flash
#   MiniCPM5-2B             <- Tiny/fastest
AMD_TEXT_MODEL: str = os.getenv(
    "AMD_TEXT_MODEL",
    "DeepSeek-V4-Flash"             # Low-latency model confirmed on AMD Token Factory
)

# ── Vision / Multimodal Model ─────────────────────────────────────────────────
# Used for: Vision Analyst node (receives base64-encoded game frames).
#
# AVAILABLE AMD VISION MODELS:
#   DeepSeek-V4-Flash-Vision-Exp <- CONFIRMED WORKING (200 OK in testing)
#   MiniCPM-V-4.7-1B             <- Tiny vision model (lower quality)
#   MiniCPM-V-4.7-35B-A3B        <- Large vision model (slower)
AMD_VISION_MODEL: str = os.getenv(
    "AMD_VISION_MODEL",
    "DeepSeek-V4-Flash-Vision-Exp"   # Confirmed working — returned 200 OK
)

# LLM inference temperature (0.1 = near-deterministic for consistent coaching)
LLM_TEMPERATURE: float = 0.1

# ==============================================================================
# SECTION 2 — Game EXE → Display Name Mapping
# ==============================================================================
# To add a new game: simply append a new entry.
# Key   = the EXACT process name visible in Task Manager / psutil (case-insensitive).
# Value = a human-readable game name (used for DB logging and web search queries).
#
# Format:
#   "executable_name.exe": "Game Display Name"

GAME_CONFIG: dict[str, str] = {
    "bloodstrike.exe":   "Blood Strike",
    "valorant.exe":      "Valorant",
    "csgo.exe":          "CS:GO",
    "cs2.exe":           "Counter-Strike 2",
    "r5apex.exe":        "Apex Legends",
    "cod.exe":           "Call of Duty",
    "overwatch.exe":     "Overwatch 2",
    "RainbowSix.exe":    "Rainbow Six Siege",
    "EscapeFromTarkov.exe": "Escape From Tarkov",
}

# ==============================================================================
# SECTION 2B — Esports Pro Benchmarks (Ground Truth Anchors)
# ==============================================================================
# Realistic competitive sensitivity ranges collected from pro telemetry & guides.
# Acts as a reliable fallback whenever web search returns generic articles without
# concrete numerical values.
PRO_BENCHMARKS: dict[str, dict] = {
    "Blood Strike": {
        "no_ads_sens": 75,
        "iron_sight_sens": 40,
        "scope_sens": 40,
        "typical_x": 75,
        "typical_y": 40,
        "range_no_ads": (55, 95),
        "range_iron_sight": (30, 55),
        "range_scope": (25, 55),
        "description": "Blood Strike integer slider menu: No ADS Steering (baseline 75), Iron Sight/Holo/Red Dot (baseline 40), Scopes 2X-8X (baseline 40).",
    },
    "Valorant": {
        "typical_x": 0.35,
        "typical_y": 0.35,
        "range_x": (0.20, 0.45),
        "range_y": (0.20, 0.45),
        "recoil_ratio_y": 1.0,
        "description": "Tactical shooter favoring low sensitivity for micro-adjustments and crosshair placement.",
    },
    "Counter-Strike 2": {
        "typical_x": 1.0,
        "typical_y": 1.0,
        "range_x": (0.7, 1.4),
        "range_y": (0.7, 1.4),
        "recoil_ratio_y": 1.0,
        "description": "Low-to-medium sens favoring consistent spray control and pixel headshots.",
    },
    "CS:GO": {
        "typical_x": 1.0,
        "typical_y": 1.0,
        "range_x": (0.7, 1.4),
        "range_y": (0.7, 1.4),
        "recoil_ratio_y": 1.0,
        "description": "Low-to-medium sens favoring consistent spray control.",
    },
    "Apex Legends": {
        "typical_x": 1.8,
        "typical_y": 1.8,
        "range_x": (1.2, 2.5),
        "range_y": (1.2, 2.5),
        "recoil_ratio_y": 1.0,
        "description": "High mobility tracking shooter favoring medium-high arm and wrist tracking.",
    },
    "Call of Duty": {
        "typical_x": 4.5,
        "typical_y": 4.5,
        "range_x": (3.5, 6.0),
        "range_y": (3.5, 6.0),
        "recoil_ratio_y": 1.0,
        "description": "Fast target acquisition with ADS multipliers.",
    },
    "Overwatch 2": {
        "typical_x": 4.8,
        "typical_y": 4.8,
        "range_x": (3.5, 6.5),
        "range_y": (3.5, 6.5),
        "recoil_ratio_y": 1.0,
        "description": "Fast 180-degree turn requirements with projectile and hitscan heroes.",
    },
    "Rainbow Six Siege": {
        "typical_x": 35.0,
        "typical_y": 35.0,
        "range_x": (25.0, 50.0),
        "range_y": (25.0, 50.0),
        "recoil_ratio_y": 1.0,
        "description": "Tactical siege shooter with higher engine raw multipliers.",
    },
    "Escape From Tarkov": {
        "typical_x": 0.35,
        "typical_y": 0.35,
        "range_x": (0.2, 0.5),
        "range_y": (0.2, 0.5),
        "recoil_ratio_y": 1.0,
        "description": "Heavy realism shooter with inertia and weapon weight mechanics.",
    },
}

def get_game_benchmark(game_name: str) -> dict:
    """Return pro benchmark for game or default sane fallback."""
    return PRO_BENCHMARKS.get(game_name, {
        "typical_x": 3.1,
        "typical_y": 3.1,
        "range_x": (2.5, 4.0),
        "range_y": (2.5, 4.0),
        "recoil_ratio_y": 1.0,
        "description": "General FPS default",
    })


# ==============================================================================
# SECTION 3 — Screen Capture Region
# ==============================================================================
# Crosshair region: a small box centred on the screen for frame capture.
# Expressed as a fraction of total screen dimensions (0.0 – 1.0).
# 0.15 = capture the middle 15% width × 15% height of the screen.

CROSSHAIR_REGION_FRACTION: float = 0.15   # Adjust to taste (smaller = faster)

# Number of rapid frames to grab per shot event
FRAMES_PER_SHOT: int = 3

# Duration (seconds) of mouse-movement data to collect per shot event
MOUSE_CAPTURE_DURATION: float = 1.0

# ==============================================================================
# SECTION 4 — Sensitivity Parameter Bounds
# ==============================================================================
# Blood Strike exact in-game UI menu settings (Settings -> Sensitivity -> Slide)
BLOOD_STRIKE_SENSITIVITY_CONFIG: dict = {
    "baselines": {
        "no_ads_sens": 75,       # "No ADS Steering - FPS" / "No ADS Steering - TPS" (Hipfire)
        "iron_sight_sens": 40,   # "Iron Sight/Holo/Red Dot" & "Tactical Stance"
        "scope_sens": 40,        # "2X, 3X, 4X, 6X, 8X Scope"
    },
    "bounds": {
        "no_ads_min": 10,
        "no_ads_max": 200,
        "iron_sight_min": 5,
        "iron_sight_max": 150,
        "scope_min": 5,
        "scope_max": 150,
    },
}

SENSITIVITY_BOUNDS: dict = {
    # Generic FPS bounds
    "x_sens_min": 0.1,
    "x_sens_max": 200.0,
    "y_sens_min": 0.1,
    "y_sens_max": 200.0,
    # Blood Strike integer slider limits
    "no_ads_min": 10,
    "no_ads_max": 200,
    "iron_sight_min": 5,
    "iron_sight_max": 150,
    "scope_min": 5,
    "scope_max": 150,
}

# ==============================================================================
# SECTION 5 — Database
# ==============================================================================
DATABASE_PATH: str = os.getenv("DB_PATH", "agenticaim.db")

# ==============================================================================
# SECTION 6 — FastAPI Server
# ==============================================================================
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int  = int(os.getenv("API_PORT", "8000"))
