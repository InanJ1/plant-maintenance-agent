"""Corvane's manuals on machina's DocumentStoreConnector.

Two Corvane-specific changes, both in a thin subclass:

1. Embeddings come from the shared Ollama (``nomic-embed-text``) instead of a
   model downloaded at runtime. machina 0.4.0 only takes a sentence-transformers
   model name, so this overrides its ``_load_embedding_function`` hook
   (internal API, pinned to machina-ai 0.4.0).
2. Asset-scoped search by family. machina filters asset-scoped searches on an
   exact ``asset_id`` match, but Corvane writes one manual per machine family
   (one spindle manual for all eight CNCs, one plant-wide lockout SOP). Each
   manual carries ``asset_family`` in its frontmatter, and a search for CNC-04
   returns chunks tagged for CNC-04, for the CNC family, or for ALL.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from machina.connectors.docs import DocumentStoreConnector

if TYPE_CHECKING:
    from pathlib import Path

    from langchain_core.embeddings import Embeddings
    from machina.connectors.docs.document_store import DocumentChunk

PLANT_WIDE = "ALL"


def asset_family(asset_id: str) -> str:
    """CNC-04 -> CNC, CMP-03 -> CMP."""
    return asset_id.split("-", 1)[0].upper()


class CorvaneDocStore(DocumentStoreConnector):
    """DocumentStoreConnector with Ollama embeddings and family-scoped search."""

    def __init__(
        self, *, paths: list[str | Path], embeddings: Embeddings | None = None, **kwargs: Any
    ) -> None:
        super().__init__(paths=paths, collection_name="corvane_manuals", **kwargs)
        self._corvane_embeddings = embeddings

    def _load_embedding_function(self) -> Any:
        if self._corvane_embeddings is not None:
            return self._corvane_embeddings
        return super()._load_embedding_function()

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        asset_id: str = "",
        filters: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        if not asset_id:
            return await super().search(query, top_k=top_k, filters=filters)
        family = asset_family(asset_id)
        # Rank the whole (small) corpus, then keep what applies to this asset.
        ranked = await super().search(query, top_k=max(top_k, len(self._chunks)), filters=filters)
        keep = [
            c for c in ranked
            if c.asset_id in ("", asset_id)
            and c.metadata.get("asset_family") in (family, PLANT_WIDE)
        ]
        return keep[:top_k]
