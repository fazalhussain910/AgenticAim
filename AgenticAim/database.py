"""
database.py — AgenticAim SQLite Database Layer
===============================================
Handles:
  • Schema creation (auto-runs on first import)
  • Logging a complete analysis session (telemetry → AI diagnosis → recommendations)
  • Fetching historical sessions for review / API endpoints

All operations use the synchronous sqlite3 stdlib so there are zero extra
install dependencies beyond what is in requirements.txt for this module.
Async wrappers (for FastAPI) use aiosqlite.

AMD Developer Hackathon | AI-Powered Esports Aim Coach
"""

import sqlite3
import aiosqlite
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from config import DATABASE_PATH

logger = logging.getLogger("agenticaim.database")

# ==============================================================================
# SCHEMA DEFINITION
# ==============================================================================

# Stores one row per "aim session" — triggered each time the full LangGraph
# pipeline completes (one left-click analysis cycle).
CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS aim_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Context ---
    timestamp           TEXT    NOT NULL,          -- ISO-8601 UTC
    game_name           TEXT    NOT NULL,          -- e.g. "Blood Strike"
    game_exe            TEXT    NOT NULL,          -- e.g. "bloodstrike.exe"

    -- Raw Telemetry (JSON blobs) ---
    mouse_deltas_json   TEXT    NOT NULL,          -- List[{dx, dy, t}] from pynput
    frame_count         INTEGER NOT NULL,          -- How many frames were captured

    -- Vision Analysis (Node 1 output) ---
    vision_raw_output   TEXT,                      -- Full LLM response text
    accuracy_score      REAL,                      -- 0.0–1.0 estimate of on-target %
    recoil_detected     INTEGER,                   -- 0 or 1 (BOOLEAN)
    recoil_severity     TEXT,                      -- "none" | "mild" | "moderate" | "severe"
    flick_diagnosis     TEXT,                      -- "over-flick" | "under-flick" | "on-target"

    -- Meta Research (Node 2 output) ---
    pro_meta_summary    TEXT,                      -- Web search summary text
    pro_x_sens          REAL,                      -- Pro-recommended X sens from search
    pro_y_sens          REAL,                      -- Pro-recommended Y sens from search

    -- Coach Recommendations (Node 3 output) ---
    coach_reasoning     TEXT,                      -- Full reasoning text from calculator
    recommended_x_sens  REAL    NOT NULL,          -- Final X sensitivity recommendation
    recommended_y_sens  REAL    NOT NULL,          -- Final Y sensitivity recommendation
    confidence_pct      INTEGER,                   -- 0–100 confidence in the recommendation

    -- Blood Strike In-Game Sliders ---
    no_ads_sens         INTEGER DEFAULT 75,        -- Blood Strike No ADS Steering
    iron_sight_sens     INTEGER DEFAULT 40,        -- Blood Strike Iron Sight / Holo / Red Dot
    scope_sens          INTEGER DEFAULT 40,        -- Blood Strike Scopes (2X to 8X)
    newbie_advice       TEXT,                      -- Beginner friendly advice

    -- Flags ---
    is_mock_data        INTEGER DEFAULT 0          -- 1 if this session used simulated data
);
"""

# ==============================================================================
# SYNC HELPERS — used during startup / terminal testing
# ==============================================================================

def init_db() -> None:
    """
    Create the database and all required tables if they don't exist.
    Safe to call multiple times (idempotent due to CREATE IF NOT EXISTS).
    Also performs lightweight column migrations if the table already existed.
    """
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(CREATE_SESSIONS_TABLE)
        cursor = conn.execute("PRAGMA table_info(aim_sessions)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        new_cols = [
            ("no_ads_sens", "INTEGER DEFAULT 75"),
            ("iron_sight_sens", "INTEGER DEFAULT 40"),
            ("scope_sens", "INTEGER DEFAULT 40"),
            ("newbie_advice", "TEXT DEFAULT ''"),
        ]
        for col_name, col_def in new_cols:
            if col_name not in existing_cols:
                try:
                    conn.execute(f"ALTER TABLE aim_sessions ADD COLUMN {col_name} {col_def}")
                except Exception as e:
                    logger.debug(f"Column migration skipped for {col_name}: {e}")
        conn.commit()
    logger.info(f"Database initialised at: {DATABASE_PATH}")


def log_session_sync(session_data: dict) -> int:
    """
    Synchronous (blocking) insert of one complete analysis session.

    Args:
        session_data: A flat dict whose keys match the aim_sessions columns.

    Returns:
        The auto-assigned row ID (int).
    """
    row = _build_row(session_data)

    sql = """
        INSERT INTO aim_sessions (
            timestamp, game_name, game_exe,
            mouse_deltas_json, frame_count,
            vision_raw_output, accuracy_score, recoil_detected,
            recoil_severity, flick_diagnosis,
            pro_meta_summary, pro_x_sens, pro_y_sens,
            coach_reasoning, recommended_x_sens, recommended_y_sens,
            no_ads_sens, iron_sight_sens, scope_sens, newbie_advice,
            confidence_pct, is_mock_data
        ) VALUES (
            :timestamp, :game_name, :game_exe,
            :mouse_deltas_json, :frame_count,
            :vision_raw_output, :accuracy_score, :recoil_detected,
            :recoil_severity, :flick_diagnosis,
            :pro_meta_summary, :pro_x_sens, :pro_y_sens,
            :coach_reasoning, :recommended_x_sens, :recommended_y_sens,
            :no_ads_sens, :iron_sight_sens, :scope_sens, :newbie_advice,
            :confidence_pct, :is_mock_data
        )
    """
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.execute(sql, row)
        conn.commit()
        row_id = cursor.lastrowid
    logger.info(f"Session logged → row ID {row_id}")
    return row_id or 0


# ==============================================================================
# ASYNC HELPERS — used by FastAPI route handlers
# ==============================================================================

async def log_session_async(session_data: dict) -> int:
    """
    Async insert of one complete analysis session (non-blocking for FastAPI).
    Identical to log_session_sync but uses aiosqlite.
    """
    row = _build_row(session_data)

    sql = """
        INSERT INTO aim_sessions (
            timestamp, game_name, game_exe,
            mouse_deltas_json, frame_count,
            vision_raw_output, accuracy_score, recoil_detected,
            recoil_severity, flick_diagnosis,
            pro_meta_summary, pro_x_sens, pro_y_sens,
            coach_reasoning, recommended_x_sens, recommended_y_sens,
            no_ads_sens, iron_sight_sens, scope_sens, newbie_advice,
            confidence_pct, is_mock_data
        ) VALUES (
            :timestamp, :game_name, :game_exe,
            :mouse_deltas_json, :frame_count,
            :vision_raw_output, :accuracy_score, :recoil_detected,
            :recoil_severity, :flick_diagnosis,
            :pro_meta_summary, :pro_x_sens, :pro_y_sens,
            :coach_reasoning, :recommended_x_sens, :recommended_y_sens,
            :no_ads_sens, :iron_sight_sens, :scope_sens, :newbie_advice,
            :confidence_pct, :is_mock_data
        )
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(sql, row)
        await db.commit()
        row_id = cursor.lastrowid
    logger.info(f"[async] Session logged → row ID {row_id}")
    return row_id or 0


def _row_to_session_dict(row: dict) -> dict:
    """
    Format a raw SQLite row into a clean, complete session dictionary
    containing derived telemetry stats, vision analysis, and in-game sensitivity sliders.
    """
    deltas = []
    if row.get("mouse_deltas_json"):
        try:
            deltas = json.loads(row["mouse_deltas_json"])
        except Exception:
            deltas = []

    total_dx = round(sum(d.get("dx", 0.0) for d in deltas), 2) if deltas else 0.0
    total_dy = round(sum(d.get("dy", 0.0) for d in deltas), 2) if deltas else 0.0
    downward_pull = round(sum(d.get("dy", 0.0) for d in deltas if d.get("dy", 0.0) > 0), 2) if deltas else 0.0
    duration = deltas[-1].get("t", 0) - deltas[0].get("t", 0) if len(deltas) > 1 else 1.0
    total_dist = sum((d.get("dx", 0.0)**2 + d.get("dy", 0.0)**2)**0.5 for d in deltas) if deltas else 0.0
    avg_speed = round(total_dist / max(duration, 0.001), 2) if deltas else 0.0

    vision_parsed = {}
    if row.get("vision_raw_output"):
        try:
            clean_json = row["vision_raw_output"].replace("```json", "").replace("```", "").strip()
            vision_parsed = json.loads(clean_json)
        except Exception:
            vision_parsed = {}

    no_ads = row.get("no_ads_sens")
    if no_ads is None or no_ads == 0:
        no_ads = int(row.get("recommended_x_sens") or 75)

    iron_sight = row.get("iron_sight_sens")
    if iron_sight is None or iron_sight == 0:
        iron_sight = int(row.get("recommended_y_sens") or 40)

    scope = row.get("scope_sens")
    if scope is None or scope == 0:
        scope = 40

    return {
        "id": row.get("id"),
        "timestamp": row.get("timestamp"),
        "game_name": row.get("game_name", "Blood Strike"),
        "game_exe": row.get("game_exe", "bloodstrike.exe"),
        "telemetry": {
            "total_dx": total_dx,
            "total_dy": total_dy,
            "downward_pull": downward_pull,
            "avg_speed_pps": avg_speed,
            "sample_count": len(deltas),
        },
        "vision_analysis": {
            "accuracy_score": float(row.get("accuracy_score") or 0.0),
            "recoil_detected": bool(row.get("recoil_detected", False)),
            "recoil_severity": row.get("recoil_severity", "none"),
            "flick_diagnosis": row.get("flick_diagnosis", "unknown"),
            "recoil_compensation_quality": vision_parsed.get("recoil_compensation_quality", "unknown"),
            "primary_weakness": vision_parsed.get("primary_weakness", ""),
            "detailed_analysis": vision_parsed.get("detailed_analysis", ""),
        },
        "sensitivity_sliders": {
            "no_ads_sens": int(no_ads),
            "iron_sight_sens": int(iron_sight),
            "scope_sens": int(scope),
        },
        "coach_reasoning": row.get("coach_reasoning", ""),
        "newbie_advice": row.get("newbie_advice") or "",
        "confidence_pct": int(row.get("confidence_pct") or 80),
        "is_mock_data": bool(row.get("is_mock_data", False)),
    }


def get_latest_session() -> Optional[dict]:
    """
    Fetch the most recently logged aim session from SQLite.
    Returns a complete dictionary with mouse telemetry, vision, and Blood Strike slider values.
    """
    sql = "SELECT * FROM aim_sessions ORDER BY id DESC LIMIT 1"
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql)
        row = cursor.fetchone()
    if not row:
        return None
    return _row_to_session_dict(dict(row))


def get_recent_sessions(limit: int = 5) -> list[dict]:
    """
    Fetch the `limit` most recently logged aim sessions from SQLite.
    Returns a list of complete session dictionaries.
    """
    sql = "SELECT * FROM aim_sessions ORDER BY id DESC LIMIT ?"
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql, (limit,))
        rows = cursor.fetchall()
    return [_row_to_session_dict(dict(r)) for r in rows]


async def fetch_recent_sessions(limit: int = 10) -> list[dict]:
    """
    Return the `limit` most recent sessions as a list of dicts.
    Used by the /history FastAPI endpoint.
    """
    sql = """
        SELECT * FROM aim_sessions
        ORDER BY id DESC
        LIMIT ?
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row  # Enables dict-like access
        async with db.execute(sql, (limit,)) as cursor:
            rows = await cursor.fetchall()
    return [_row_to_session_dict(dict(r)) for r in rows]


async def fetch_session_by_id(session_id: int) -> Optional[dict]:
    """
    Fetch a single session by its primary key. Returns None if not found.
    """
    sql = "SELECT * FROM aim_sessions WHERE id = ?"
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, (session_id,)) as cursor:
            row = await cursor.fetchone()
    return _row_to_session_dict(dict(row)) if row else None


# ==============================================================================
# PRIVATE HELPERS
# ==============================================================================

def _build_row(data: dict) -> dict:
    """
    Normalise and fill in defaults for a session row dict before INSERT.
    Ensures mouse_deltas_json is always a JSON string, never a raw Python list.
    """
    row = dict(data)  # Shallow copy — don't mutate caller's dict

    # Serialise the mouse delta list to JSON if the caller passed a Python list
    if isinstance(row.get("mouse_deltas_json"), list):
        row["mouse_deltas_json"] = json.dumps(row["mouse_deltas_json"])

    # Default timestamp to now (UTC) if not supplied
    if not row.get("timestamp"):
        row["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Boolean to int for SQLite
    row["recoil_detected"] = int(bool(row.get("recoil_detected", 0)))
    row["is_mock_data"]    = int(bool(row.get("is_mock_data", 0)))

    # In-game sliders & beginner advice
    row["no_ads_sens"]     = int(row.get("no_ads_sens") or row.get("recommended_x_sens") or 75)
    row["iron_sight_sens"] = int(row.get("iron_sight_sens") or row.get("recommended_y_sens") or 40)
    row["scope_sens"]      = int(row.get("scope_sens") or 40)
    row["newbie_advice"]   = str(row.get("newbie_advice") or "")

    return row
