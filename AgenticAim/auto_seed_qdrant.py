"""
auto_seed_qdrant.py — Autonomous Knowledge Base Builder & Qdrant Seeder
========================================================================
Parses bloodstrike_pro_guide.txt into structured knowledge chunks,
generates 768-dim vectors matching nomic-embed-text, and upserts them
into the Qdrant Cloud 'bloodstrike_knowledge' collection.

AMD Developer Hackathon | AI-Powered Esports Aim Coach
"""

import os
import re
import uuid
import logging
from qdrant_client.http import models as qmodels
from rag import _get_qdrant, embed_text, KNOWLEDGE_COLL, _ensure_collection, EMBED_DIM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agenticaim.auto_seeder")


def parse_guide_file(filepath: str = "bloodstrike_pro_guide.txt") -> list[dict]:
    """Parse section blocks from guide file into structured chunks."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Guide file not found at: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on [SECTION: ...] headers
    raw_sections = re.split(r"\[SECTION:\s*([^\]]+)\]", content)
    docs = []

    # raw_sections[0] is header preamble; subsequent elements are (title, body) pairs
    i = 1
    while i < len(raw_sections):
        title = raw_sections[i].strip()
        body = raw_sections[i + 1].strip() if i + 1 < len(raw_sections) else ""
        if title and body:
            category = re.sub(r"[^a-zA-Z0-9_]+", "_", title.lower()).strip("_")
            chunk_id = f"bs_pro_{category[:30]}"
            full_text = f"[{title}]\n{body}"
            docs.append({
                "id": chunk_id,
                "title": title,
                "category": category,
                "text": full_text,
            })
        i += 2

    return docs


def seed_qdrant_knowledge(docs: list[dict]) -> int:
    """Embed chunks into 768-dim vectors and upsert into Qdrant Cloud."""
    client = _get_qdrant()
    if client is None:
        raise RuntimeError("Qdrant client could not connect. Check QDRANT_URL and QDRANT_API_KEY in .env.")

    # Enforce 768-dim collection
    _ensure_collection(client, KNOWLEDGE_COLL, EMBED_DIM)

    points = []
    logger.info(f"Embedding {len(docs)} knowledge chunks (target dim={EMBED_DIM})...")

    for doc in docs:
        vec, dim = embed_text(doc["text"])
        # Ensure exact dimension
        vec = (vec + [0.0] * EMBED_DIM)[:EMBED_DIM]
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc["id"]))

        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vec,
                payload={
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "text": doc["text"],
                    "source": "bloodstrike_pro_guide.txt",
                },
            )
        )

    client.upsert(collection_name=KNOWLEDGE_COLL, points=points)
    total_count = client.get_collection(KNOWLEDGE_COLL).points_count
    logger.info(f"✅ Successfully seeded {len(points)} chunks into '{KNOWLEDGE_COLL}'!")
    logger.info(f"📊 Total collection points: {total_count} (Vector Dimension: {EMBED_DIM})")
    return total_count


if __name__ == "__main__":
    logger.info("═══ Starting Autonomous Qdrant Seeder ═══")
    chunks = parse_guide_file("bloodstrike_pro_guide.txt")
    logger.info(f"Parsed {len(chunks)} knowledge chunks from bloodstrike_pro_guide.txt:")
    for c in chunks:
        logger.info(f"  • {c['title']} ({len(c['text'])} chars)")
    
    total = seed_qdrant_knowledge(chunks)
    logger.info(f"═══ Seeding Complete! Collection points: {total} ═══")
