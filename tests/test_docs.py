"""Family-scoped manual search, with an offline stand-in embedder (no Ollama needed)."""

from __future__ import annotations

import hashlib
import math

from langchain_core.embeddings import Embeddings

from corvane_pm.config import MANUALS_DIR
from corvane_pm.docs import CorvaneDocStore, asset_family


class HashEmbeddings(Embeddings):
    """Bag-of-words hashed into 256 dims: deterministic and good enough for a filter test."""

    def _vec(self, text):
        v = [0.0] * 256
        for word in text.lower().split():
            v[int(hashlib.md5(word.encode()).hexdigest(), 16) % 256] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


def test_asset_family():
    assert asset_family("CNC-04") == "CNC"
    assert asset_family("cmp-03") == "CMP"


async def test_search_keeps_family_and_plant_wide_docs():
    store = CorvaneDocStore(paths=[MANUALS_DIR], embeddings=HashEmbeddings())
    await store.connect()
    try:
        health = await store.health_check()
        assert health.details["mode"] == "rag"
        hits = await store.search("lockout before opening the cooler", asset_id="CMP-03", top_k=5)
        families = {h.metadata.get("asset_family") for h in hits}
        assert hits and families <= {"CMP", "ALL"}
        assert any("lockout" in h.source for h in hits)
        cnc = await store.search("bearing replacement procedure", asset_id="CNC-04", top_k=5)
        assert cnc and {h.metadata.get("asset_family") for h in cnc} <= {"CNC", "ALL"}
    finally:
        await store.disconnect()
