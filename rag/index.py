"""
RAG indexer — builds the ChromaDB collection from the asset library.

Run this once (or whenever the asset library changes):

    python -m rag.index

The collection is persisted to ./rag/chroma_db/ so it survives restarts.
Embeddings are generated via Ollama (must be running with qwen3-embedding:8b pulled).
"""

import sys
import time
from pathlib import Path

import chromadb
import ollama

from rag.assets import ASSETS

EMBED_MODEL = "qwen3-embedding:8b"
CHROMA_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "holodeck_assets"


def get_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def embed(text: str) -> list[float]:
    response = ollama.embed(model=EMBED_MODEL, input=text)
    return response["embeddings"][0]


def build_index(reset: bool = False) -> None:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"Deleted existing collection '{COLLECTION_NAME}'.")
        except Exception:
            pass

    collection = get_collection(client)
    existing_ids = set(collection.get()["ids"])

    added = 0
    skipped = 0

    for asset in ASSETS:
        asset_id = asset["name"]

        if asset_id in existing_ids:
            skipped += 1
            continue

        t0 = time.perf_counter()
        vector = embed(asset["description"])
        elapsed = time.perf_counter() - t0

        collection.add(
            ids=[asset_id],
            embeddings=[vector],
            documents=[asset["description"]],
            metadatas=[{"name": asset["name"], "url": asset["url"]}],
        )

        print(f"  [+] {asset['name']:<30} ({elapsed:.2f}s)")
        added += 1

    print(f"\nDone. {added} added, {skipped} skipped (already indexed).")
    print(f"Collection size: {collection.count()} assets.")


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    if reset_flag:
        print("--reset flag set: rebuilding index from scratch.")
    print(f"Indexing {len(ASSETS)} assets with {EMBED_MODEL}...\n")
    build_index(reset=reset_flag)
