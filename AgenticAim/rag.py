"""
rag.py — AgenticAim Hybrid RAG + Adaptive Personal Memory
===========================================================
Provides two vector-search capabilities on top of Qdrant (local or Cloud):

  Collection 1 — bloodstrike_knowledge
    Static weapon stats, recoil patterns, and pro tracking drills.
    Seeded once from BLOOD_STRIKE_KNOWLEDGE_DOCS at startup.

  Collection 2 — player_memory
    Per-session telemetry + coaching feedback. Stored with session_id as the
    Qdrant Point ID for idempotent upserts (duplicate-safe).

Embedding strategy (RAM-light for Ryzen 5 / 8 GB):
  Primary  : AMD Token Factory API (text-embedding-3-small compatible, dim=1536)
  Fallback : Deterministic SHA-256 hash fingerprint (256-dim pseudo-vector)
             so the coaching pipeline NEVER crashes on embedding timeouts.

CRITICAL RULE: This module is purely additive — it does NOT modify the
existing 4-node LangGraph topology in graph.py.

AMD Developer Hackathon | AI-Powered Esports Aim Coach
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
    _QDRANT_OK = True
except ImportError:
    _QDRANT_OK = False

try:
    from openai import OpenAI as _OpenAI
    _OPENAI_OK = True
except ImportError:
    _OPENAI_OK = False

from config import AMD_API_KEY, AMD_BASE_URL

logger = logging.getLogger("agenticaim.rag")

# ---------------------------------------------------------------------------
# Constants & env-driven Qdrant connection settings
# ---------------------------------------------------------------------------
AMD_EMBED_MODEL = os.getenv("AMD_EMBED_MODEL", "nomic-embed-text")

# Dimension mappings for supported embedding models
DEFAULT_DIM_MAP = {
    "nomic-embed-text": 768,
    "nomic-ai/nomic-embed-text-v1.5": 768,
    "text-embedding-3-small": 1536,
    "bge-small-en-v1.5": 384,
    "bge-large-en-v1.5": 1024,
}
EMBED_DIM      = int(os.getenv("EMBED_DIM", str(DEFAULT_DIM_MAP.get(AMD_EMBED_MODEL, 768))))
FALLBACK_DIM   = EMBED_DIM     # Exactly matches target model dimension (768)
KNOWLEDGE_COLL = "bloodstrike_knowledge"
MEMORY_COLL    = "player_memory"

QDRANT_URL     = os.getenv("QDRANT_URL", "")            # cloud URL (highest priority)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")        # cloud API key
QDRANT_HOST    = os.getenv("QDRANT_HOST", "localhost")   # local fallback
QDRANT_PORT    = int(os.getenv("QDRANT_PORT", "6333"))   # local fallback

_USE_CLOUD = bool(QDRANT_URL)

# ---------------------------------------------------------------------------
# Static Blood Strike Knowledge Documents  (seeded once into Qdrant)
# ---------------------------------------------------------------------------
BLOOD_STRIKE_KNOWLEDGE_DOCS: list[dict] = [
    {
        "id": "bs_recoil_001",
        "text": (
            "Blood Strike weapon recoil fundamentals: Every automatic weapon in Blood Strike "
            "has a vertical recoil pattern. The standard AR kicks upward ~8-12 px per burst. "
            "Counter-pull (downward_pull) of 70-90 px/s is required at medium range. "
            "Burst firing (3-5 rounds) reduces effective recoil by 60%."
        ),
        "category": "recoil_mechanics",
    },
    {
        "id": "bs_sensitivity_001",
        "text": (
            "Blood Strike optimal sensitivity: No ADS Steering baseline 75 — reduce to 60-65 "
            "for over-flick players (dx > 80px). Iron Sight baseline 40 — raise to 45-50 for "
            "under-compensated recoil (downward_pull < 40px). Scopes baseline 40 — never "
            "exceed 50 for stable long-range shots."
        ),
        "category": "sensitivity_calibration",
    },
    {
        "id": "bs_tracking_drills_001",
        "text": (
            "Blood Strike 5-minute warm-up drill: "
            "1. Training mode, pick AR. "
            "2. Spray 10 rounds at wall from 20m — observe drift. "
            "3. Crosshair drifts RIGHT after 5 bullets: increase No ADS by 3. "
            "4. Crosshair overshoots UP: practice counter-pull. "
            "5. Track moving bots at medium range for 2 min. "
            "Run before every ranked match for consistent mechanical performance."
        ),
        "category": "training_drills",
    },
    {
        "id": "bs_crosshair_placement_001",
        "text": (
            "Blood Strike crosshair placement: pre-aim head/chest level at corner entries. "
            "Crosshair dropping to waist-level during movement costs 0.2-0.4s reaction time. "
            "Keep crosshair on the EDGE of cover, not center-screen. "
            "Pre-aiming is worth more than any sensitivity adjustment."
        ),
        "category": "crosshair_placement",
    },
    {
        "id": "bs_flick_mechanics_001",
        "text": (
            "Blood Strike flick mechanics: healthy flick dx is 15-60px at close range. "
            "dx > 80px = over-flick — reduce No ADS by 5-10 points. "
            "dx < 10px with low accuracy = under-tracking — player not following lateral "
            "enemy movement. Practice muscle memory at 1.5x usual dx range in training mode."
        ),
        "category": "flick_mechanics",
    },
    {
        "id": "bs_hardware_001",
        "text": (
            "Blood Strike PC performance: RAM above 85% adds 8-15ms input latency per frame. "
            "Close browser tabs and Discord video before ranked. CPU above 80% degrades "
            "physics update loop. Target: CPU < 70%, RAM < 80% for tournament-grade response."
        ),
        "category": "hardware_performance",
    },
    {
        "id": "bs_weapon_meta_001",
        "text": (
            "Blood Strike weapon meta: AR class is most forgiving for recoil learners. "
            "SMG has near-zero recoil <10m but degrades >25m. Snipers need zero spray — "
            "focus on pre-aim and target stillness. LMG rewards counter-pull mastery "
            "with highest sustained DPS."
        ),
        "category": "weapon_meta",
    },
    {
        "id": "bs_ranked_tips_001",
        "text": (
            "Blood Strike ranked habits: "
            "1. Check hardware (RAM < 85%, CPU < 80%) before queuing. "
            "2. Run 5-min warm-up drill first. "
            "3. Pick ONE mechanic per session (crosshair placement OR recoil). "
            "4. Use post-match telemetry to track dx/downward_pull trends. "
            "5. Only change sensitivity after 3+ sessions showing the same issue."
        ),
        "category": "ranked_strategy",
    },
]

# ---------------------------------------------------------------------------
# Singleton caches
# ---------------------------------------------------------------------------
_qdrant_client: Optional[QdrantClient] = None
_embed_client: Optional[Any]           = None
_fallback_mode: bool                   = False


# ---------------------------------------------------------------------------
# Qdrant client
# ---------------------------------------------------------------------------
def _get_qdrant() -> Optional[QdrantClient]:
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client
    if not _QDRANT_OK:
        logger.warning("qdrant-client not installed — RAG disabled.")
        return None
    try:
        if _USE_CLOUD:
            _qdrant_client = QdrantClient(
                url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=10
            )
        else:
            _qdrant_client = QdrantClient(
                host=QDRANT_HOST, port=QDRANT_PORT, timeout=5
            )
        _qdrant_client.get_collections()   # connectivity probe
        logger.info(f"Qdrant connected ({'cloud' if _USE_CLOUD else f'{QDRANT_HOST}:{QDRANT_PORT}'}).")
    except Exception as e:
        logger.warning(f"Qdrant unavailable ({e}) — RAG context will be empty (non-fatal).")
        _qdrant_client = None
    return _qdrant_client


# ---------------------------------------------------------------------------
# Embedding client
# ---------------------------------------------------------------------------
def _get_embed_client() -> Optional[Any]:
    global _embed_client
    if _embed_client is not None:
        return _embed_client
    if not _OPENAI_OK:
        return None
    try:
        _embed_client = _OpenAI(base_url=AMD_BASE_URL, api_key=AMD_API_KEY)
        logger.info("Embedding client ready (AMD Token Factory).")
    except Exception as e:
        logger.warning(f"Embed client init failed: {e}")
    return _embed_client


# ---------------------------------------------------------------------------
# Fallback: deterministic hash pseudo-embedding (never fails)
# ---------------------------------------------------------------------------
def _hash_embed(text: str, dim: int = FALLBACK_DIM) -> list[float]:
    raw = hashlib.sha256(text.encode("utf-8")).digest()
    repeats = math.ceil(dim * 4 / len(raw))
    blob = (raw * repeats)[: dim * 4]
    ints = [
        int.from_bytes(blob[i * 4: i * 4 + 4], "big", signed=False)
        for i in range(dim)
    ]
    total = sum(ints) or 1
    return [v / total for v in ints]


# ---------------------------------------------------------------------------
# Public embed helper — tries AMD API, falls back to hash
# ---------------------------------------------------------------------------
def embed_text(text: str, retries: int = 2) -> tuple[list[float], int]:
    """
    Returns (vector, dim).
    Primary: AMD Token Factory / external OpenAI-compatible embedding API.
    Model: AMD_EMBED_MODEL (defaults to nomic-embed-text, dim=768).
    Fallback: Normalized SHA-256 hash pseudo-vector matching exact EMBED_DIM (768).
    """
    global _fallback_mode
    if _fallback_mode:
        return _hash_embed(text, dim=EMBED_DIM), EMBED_DIM

    client = _get_embed_client()
    if client is None:
        _fallback_mode = True
        return _hash_embed(text, dim=EMBED_DIM), EMBED_DIM

    for attempt in range(retries):
        try:
            resp = client.embeddings.create(
                model=AMD_EMBED_MODEL,
                input=text,
            )
            vec = resp.data[0].embedding
            return vec, len(vec)
        except Exception as e:
            err_str = str(e).lower()
            if "404" in err_str or "model_not_found" in err_str or "not available" in err_str:
                logger.info(
                    f"External embedding model '{AMD_EMBED_MODEL}' not hosted on this endpoint — "
                    f"using deterministic {EMBED_DIM}-dim vector matching collection schema."
                )
                _fallback_mode = True
                return _hash_embed(text, dim=EMBED_DIM), EMBED_DIM
            logger.warning(f"Embed attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(0.5)

    logger.info(f"Switched to deterministic {EMBED_DIM}-dim vector fallback.")
    _fallback_mode = True
    return _hash_embed(text, dim=EMBED_DIM), EMBED_DIM


# ---------------------------------------------------------------------------
# Collection helpers
# ---------------------------------------------------------------------------
def _ensure_collection(client: QdrantClient, name: str, dim: int) -> None:
    need_create = True
    try:
        coll = client.get_collection(name)
        existing_dim = getattr(getattr(coll.config.params, "vectors", None), "size", None)
        if existing_dim == dim:
            need_create = False
        else:
            logger.warning(
                f"Collection '{name}' dimension mismatch (found {existing_dim}, expected {dim}). "
                f"Recreating with dim={dim}..."
            )
            client.delete_collection(name)
            need_create = True
    except Exception:
        need_create = True

    if need_create:
        client.create_collection(
            collection_name=name,
            vectors_config=qmodels.VectorParams(
                size=dim, distance=qmodels.Distance.COSINE
            ),
        )
        logger.info(f"Created Qdrant collection '{name}' (dim={dim}).")

    if name == MEMORY_COLL:
        try:
            client.create_payload_index(
                collection_name=MEMORY_COLL,
                field_name="player_id",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass  # Index already exists or non-fatal


def _seed_knowledge(client: QdrantClient, dim: int) -> None:
    points = []
    for doc in BLOOD_STRIKE_KNOWLEDGE_DOCS:
        vec, _ = embed_text(doc["text"])
        vec = (vec + [0.0] * dim)[:dim]   # ensure correct length
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc["id"]))
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vec,
                payload={
                    "doc_id":   doc["id"],
                    "text":     doc["text"],
                    "category": doc["category"],
                },
            )
        )
    if points:
        client.upsert(collection_name=KNOWLEDGE_COLL, points=points)
        logger.info(f"Seeded {len(points)} docs into '{KNOWLEDGE_COLL}'.")


# ---------------------------------------------------------------------------
# Public API — called from graph.py RAG nodes
# ---------------------------------------------------------------------------

def init_qdrant_collections() -> bool:
    """
    Idempotent: creates/verifies both collections, seeds knowledge base if empty.
    Returns True on success, False (non-fatal) if Qdrant is unavailable.
    """
    client = _get_qdrant()
    if client is None:
        return False
    try:
        vec, dim = embed_text("warm-up connectivity test", retries=1)
        _ensure_collection(client, KNOWLEDGE_COLL, dim)
        _ensure_collection(client, MEMORY_COLL, dim)
        info = client.get_collection(KNOWLEDGE_COLL)
        if info.points_count == 0:
            logger.info("Seeding bloodstrike_knowledge collection...")
            _seed_knowledge(client, dim)
        logger.info("Qdrant collections ready.")
        return True
    except Exception as e:
        logger.error(f"Qdrant setup failed (non-fatal): {e}")
        return False


def retrieve_knowledge(query: str, top_k: int = 3) -> str:
    """
    Cosine-similarity search on `bloodstrike_knowledge`.
    Returns formatted knowledge snippets, or "" if Qdrant is unavailable.
    """
    client = _get_qdrant()
    if client is None:
        return ""
    try:
        vec, _ = embed_text(query)
        if hasattr(client, "query_points"):
            res = client.query_points(
                collection_name=KNOWLEDGE_COLL,
                query=vec,
                limit=top_k,
                with_payload=True,
            )
            hits = getattr(res, "points", res)
        elif hasattr(client, "search"):
            hits = client.search(
                collection_name=KNOWLEDGE_COLL,
                query_vector=vec,
                limit=top_k,
                with_payload=True,
            )
        else:
            hits = []

        if not hits:
            return ""
        snippets = []
        for i, h in enumerate(hits, 1):
            cat = h.payload.get("category", "general")
            txt = h.payload.get("text", "")
            snippets.append(f"[KB-{i} | {cat}] {txt}")
        return "\n".join(snippets)
    except Exception as e:
        logger.warning(f"retrieve_knowledge failed (non-fatal): {e}")
        return ""


def retrieve_player_memory(player_id: str = "default", top_n: int = 5) -> str:
    """
    Fetches most recent `top_n` sessions for `player_id` using Qdrant metadata
    FILTER + timestamp DESC ordering — NOT pure vector similarity.
    Returns formatted summary, or "" if unavailable.
    """
    client = _get_qdrant()
    if client is None:
        return ""
    try:
        results, _ = client.scroll(
            collection_name=MEMORY_COLL,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="player_id",
                        match=qmodels.MatchValue(value=player_id),
                    )
                ]
            ),
            limit=max(top_n * 2, 20),
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            return ""

        # Sort descending by timestamp_unix in Python (handles indexed & unindexed Qdrant schemas)
        sorted_results = sorted(
            results,
            key=lambda pt: (pt.payload or {}).get("timestamp_unix", 0),
            reverse=True,
        )[:top_n]

        lines = ["RECENT PLAYER HISTORY (most-recent first):"]
        for i, pt in enumerate(sorted_results, 1):
            p = pt.payload
            lines.append(
                f"  #{i} [{p.get('timestamp', '?')}]"
                f" dx={p.get('dx', '?')}px"
                f" dy={p.get('dy', '?')}px"
                f" pull={p.get('downward_pull', '?')}px"
                f" acc={p.get('accuracy_score', '?')}"
                f" flick={p.get('flick_diagnosis', '?')}"
                f" recoil={p.get('recoil_severity', '?')}"
                f" No_ADS={p.get('no_ads_sens', '?')}"
                f" Iron={p.get('iron_sight_sens', '?')}"
                f" Scope={p.get('scope_sens', '?')}"
                f" | advice: {str(p.get('coach_advice', ''))[:100]}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"retrieve_player_memory failed (non-fatal): {e}")
        return ""


def store_player_memory(
    session_id: int,
    player_id: str,
    telemetry: dict,
    vision: dict,
    sliders: dict,
    coach_advice: str,
) -> bool:
    """
    Idempotent upsert of one session into `player_memory`.
    Uses deterministic UUID derived from session_id as Point ID.

    Returns True on success, False (non-fatal) on failure.
    """
    client = _get_qdrant()
    if client is None:
        return False
    try:
        now      = datetime.now(timezone.utc)
        ts_str   = now.isoformat()
        ts_unix  = int(now.timestamp())

        summary_text = (
            f"Player {player_id}: "
            f"dx={telemetry.get('total_dx', 0)}px "
            f"dy={telemetry.get('total_dy', 0)}px "
            f"pull={telemetry.get('downward_pull', 0)}px "
            f"speed={telemetry.get('avg_speed_pps', 0)}px/s "
            f"acc={vision.get('accuracy_score', 0)} "
            f"recoil={vision.get('recoil_severity', 'none')} "
            f"flick={vision.get('flick_diagnosis', 'unknown')} "
            f"No_ADS={sliders.get('no_ads_sens', 75)} "
            f"Iron={sliders.get('iron_sight_sens', 40)} "
            f"Scope={sliders.get('scope_sens', 40)} "
            f"advice: {coach_advice[:200]}"
        )

        vec, dim = embed_text(summary_text)
        _ensure_collection(client, MEMORY_COLL, dim)

        point_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"agenticaim_session_{session_id}"))

        client.upsert(
            collection_name=MEMORY_COLL,
            points=[
                qmodels.PointStruct(
                    id=point_id,
                    vector=vec,
                    payload={
                        "session_id":      session_id,
                        "player_id":       player_id,
                        "timestamp":       ts_str,
                        "timestamp_unix":  ts_unix,
                        "dx":              telemetry.get("total_dx", 0),
                        "dy":              telemetry.get("total_dy", 0),
                        "downward_pull":   telemetry.get("downward_pull", 0),
                        "avg_speed_pps":   telemetry.get("avg_speed_pps", 0),
                        "accuracy_score":  vision.get("accuracy_score", 0),
                        "recoil_severity": vision.get("recoil_severity", "none"),
                        "flick_diagnosis": vision.get("flick_diagnosis", "unknown"),
                        "no_ads_sens":     sliders.get("no_ads_sens", 75),
                        "iron_sight_sens": sliders.get("iron_sight_sens", 40),
                        "scope_sens":      sliders.get("scope_sens", 40),
                        "coach_advice":    coach_advice[:512],
                    },
                )
            ],
        )
        logger.info(f"Stored session {session_id} for player '{player_id}' in Qdrant.")
        return True
    except Exception as e:
        logger.warning(f"store_player_memory failed (non-fatal, session {session_id}): {e}")
        return False
