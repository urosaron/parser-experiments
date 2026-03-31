"""
RAG query layer — resolves a natural-language asset_query to a CDN URL.

Usage:
    from rag.query import AssetResolver

    resolver = AssetResolver()          # loads (or creates) the collection
    url = resolver.resolve("oak chair") # returns URL string or None
"""

from pathlib import Path

import chromadb
import ollama

from rag.index import CHROMA_PATH, COLLECTION_NAME, EMBED_MODEL, get_collection

# Thresholds from rag.md §4.3
THRESHOLD_STRONG = 0.85
THRESHOLD_WEAK = 0.75


class AssetNotIndexedError(RuntimeError):
    """Raised when the ChromaDB collection is empty (index not built yet)."""


class AssetResolver:
    def __init__(self) -> None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self._collection = get_collection(client)

        if self._collection.count() == 0:
            raise AssetNotIndexedError(
                "The asset index is empty. Run 'python -m rag.index' first."
            )

    def resolve(
        self, asset_query: str
    ) -> tuple[str | None, float, str]:
        """
        Look up the best-matching CDN URL for a natural-language query.

        Returns:
            (url, score, name)
              url   — CDN URL string, or None if score is below THRESHOLD_WEAK
              score — cosine similarity in [0, 1] (higher = better)
              name  — matched asset name (useful for logging even on failure)
        """
        vector = ollama.embed(model=EMBED_MODEL, input=asset_query)["embeddings"][0]

        results = self._collection.query(
            query_embeddings=[vector],
            n_results=1,
            include=["metadatas", "distances"],
        )

        distance: float = results["distances"][0][0]
        # ChromaDB cosine space returns 1 - cosine_similarity as distance
        score: float = 1.0 - distance

        metadata: dict = results["metadatas"][0][0]
        name: str = metadata["name"]
        url: str = metadata["url"]

        if score < THRESHOLD_WEAK:
            return None, score, name

        return url, score, name

    def resolve_url(self, asset_query: str) -> str | None:
        """Convenience wrapper — returns just the URL or None."""
        url, _score, _name = self.resolve(asset_query)
        return url
