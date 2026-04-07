"""
Detailed trace of a single spawn command through the full pipeline.

Runs the same transcript N times and prints every internal step so you
can review exactly what each component does and how the result varies
across runs.

Steps shown for each run:
  1. SYSTEM PROMPT  — what the LLM is told to do
  2. USER MESSAGE   — the actual input sent to the LLM
  3. LLM RAW OUTPUT — exactly what the model returned (before any parsing)
  4. PARSED COMMAND — the JSON we extracted from that output
  5. RAG INPUT      — the asset_query string that goes into the vector search
  6. EMBEDDING      — the query vector (first 8 dims shown, plus total length)
  7. CHROMA RESULT  — top-3 nearest neighbours with scores and URLs
  8. FINAL COMMAND  — the fully resolved command with asset_url substituted in

Usage:
    python trace_spawn.py
    python trace_spawn.py --transcript "put a wooden chair here" --runs 3
    python trace_spawn.py --model qwen3.5:9b
"""

import argparse
import json
import textwrap
import time

import chromadb
import ollama

from rag.index import CHROMA_PATH, COLLECTION_NAME, EMBED_MODEL, get_collection
from rag.query import THRESHOLD_STRONG, THRESHOLD_WEAK
from test_parser import MODEL_NAME, SYSTEM_PROMPT, build_user_message, _strip_markdown_fence

# ── Default inputs — edit these or pass via CLI args ──────────────────────────

DEFAULT_TRANSCRIPT = "spawn a wooden chair near the window"

DEFAULT_USER_CONTEXT = {
    "id": "user_1",
    "position": {"x": 0, "y": 1.7, "z": 3},
    "look_direction": {"x": 0, "y": 0, "z": -1},
    "point_target": None,
}

DEFAULT_SCENE = [
    {
        "id": "server_w001",
        "name": "Window Frame",
        "metadata": {"type": "plane", "label": "Window Frame"},
        "position": {"x": 0, "y": 1, "z": -5},
    }
]

DEFAULT_RUNS = 5

# ── Helpers ───────────────────────────────────────────────────────────────────

SEP_THICK = "═" * 80
SEP_THIN  = "─" * 80
SEP_STEP  = "  " + "·" * 76


def _fmt_vector(v: list[float]) -> str:
    preview = ", ".join(f"{x:.4f}" for x in v[:8])
    return f"[{preview}, ...] ({len(v)} dimensions total)"


def _score_label(score: float) -> str:
    if score >= THRESHOLD_STRONG:
        return f"STRONG  (>= {THRESHOLD_STRONG})"
    if score >= THRESHOLD_WEAK:
        return f"WEAK    (>= {THRESHOLD_WEAK})"
    return f"MISS    (<  {THRESHOLD_WEAK})"


def _wrap(text: str, indent: int = 4) -> str:
    pad = " " * indent
    return textwrap.fill(text, width=80, initial_indent=pad, subsequent_indent=pad)


# ── Main trace ────────────────────────────────────────────────────────────────

def run_trace(transcript: str, model: str, runs: int) -> None:
    print(SEP_THICK)
    print(f"  SPAWN PIPELINE TRACE")
    print(f"  Transcript : \"{transcript}\"")
    print(f"  LLM model  : {model}")
    print(f"  Embed model: {EMBED_MODEL}")
    print(f"  Runs       : {runs}")
    print(SEP_THICK)

    # Load Chroma collection once — shared across all runs
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = get_collection(chroma_client)
    if collection.count() == 0:
        print("\n[ERROR] Chroma index is empty. Run: python -m rag.index\n")
        return

    user_message = build_user_message(transcript, DEFAULT_USER_CONTEXT, DEFAULT_SCENE)

    for run_n in range(1, runs + 1):
        print(f"\n{SEP_THICK}")
        print(f"  RUN {run_n} / {runs}")
        print(SEP_THICK)

        # ── STEP 1: System prompt ─────────────────────────────────────────────
        print(f"\n  STEP 1 — SYSTEM PROMPT  (sent to LLM every call)")
        print(SEP_THIN)
        for line in SYSTEM_PROMPT.strip().splitlines():
            print(f"    {line}")

        # ── STEP 2: User message ──────────────────────────────────────────────
        print(f"\n  STEP 2 — USER MESSAGE  (the specific input for this transcript)")
        print(SEP_THIN)
        for line in user_message.splitlines():
            print(f"    {line}")

        # ── STEP 3: LLM call ──────────────────────────────────────────────────
        print(f"\n  STEP 3 — LLM CALL  (calling {model} via Ollama...)")
        print(SEP_THIN)
        t0 = time.perf_counter()
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            options={"num_predict": 2048},
        )
        llm_elapsed = time.perf_counter() - t0
        raw_output = response["message"]["content"]

        print(f"    Elapsed  : {llm_elapsed:.2f}s")
        print(f"    Raw output (exactly what the model returned):")
        print(SEP_STEP)
        for line in raw_output.splitlines():
            print(f"    {line}")
        print(SEP_STEP)

        # ── STEP 4: Parse JSON ────────────────────────────────────────────────
        print(f"\n  STEP 4 — JSON PARSE  (strip markdown fence if present, parse JSON)")
        print(SEP_THIN)
        cleaned = _strip_markdown_fence(raw_output)
        try:
            command = json.loads(cleaned)
            print(f"    Parse    : OK")
            print(f"    Command  :")
            for line in json.dumps(command, indent=6).splitlines():
                print(f"    {line}")
        except json.JSONDecodeError as e:
            print(f"    Parse    : FAILED — {e}")
            print(f"    Cleaned string that failed to parse:")
            print(f"    {repr(cleaned)}")
            print(f"\n  [Skipping RAG — no valid JSON to work with]")
            continue

        # ── Check if this is actually a spawn ─────────────────────────────────
        if command.get("command") != "spawn":
            print(f"\n  [Command is '{command.get('command')}', not 'spawn' — skipping RAG steps]")
            continue

        asset_query = command.get("asset_query", "").strip()
        if not asset_query:
            print(f"\n  [Spawn command has no asset_query field — cannot resolve]")
            continue

        # ── STEP 5: RAG input ─────────────────────────────────────────────────
        print(f"\n  STEP 5 — RAG INPUT  (what gets sent to the embedding model)")
        print(SEP_THIN)
        print(f"    asset_query : \"{asset_query}\"")
        print(f"    (This was extracted from the LLM output above)")

        # ── STEP 6: Embed the query ───────────────────────────────────────────
        print(f"\n  STEP 6 — EMBEDDING  (asset_query → vector via {EMBED_MODEL})")
        print(SEP_THIN)
        t0 = time.perf_counter()
        embed_response = ollama.embed(model=EMBED_MODEL, input=asset_query)
        embed_elapsed = time.perf_counter() - t0
        query_vector = embed_response["embeddings"][0]
        print(f"    Elapsed    : {embed_elapsed:.3f}s")
        print(f"    Vector     : {_fmt_vector(query_vector)}")

        # ── STEP 7: Chroma query — top 3 results ─────────────────────────────
        print(f"\n  STEP 7 — CHROMA VECTOR SEARCH  (nearest neighbours in asset index)")
        print(SEP_THIN)
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=min(3, collection.count()),
            include=["metadatas", "distances", "documents"],
        )
        print(f"    Top {len(results['distances'][0])} nearest neighbours:")
        for rank, (dist, meta, doc) in enumerate(zip(
            results["distances"][0],
            results["metadatas"][0],
            results["documents"][0],
        ), start=1):
            score = 1.0 - dist
            label = _score_label(score)
            chosen = "  ← CHOSEN" if rank == 1 and score >= THRESHOLD_WEAK else (
                "  ← BELOW THRESHOLD (would return None)" if rank == 1 else ""
            )
            print(f"")
            print(f"      Rank {rank}")
            print(f"        Name        : {meta['name']}")
            print(f"        Description : {doc}")
            print(f"        Score       : {score:.4f}  ({label}){chosen}")
            print(f"        URL         : {meta['url']}")

        # ── STEP 8: Final command ─────────────────────────────────────────────
        best_score = 1.0 - results["distances"][0][0]
        best_meta  = results["metadatas"][0][0]

        print(f"\n  STEP 8 — FINAL COMMAND  (asset_query replaced by resolved asset_url)")
        print(SEP_THIN)

        final = dict(command)
        final.pop("asset_query", None)

        if best_score >= THRESHOLD_WEAK:
            final["asset_url"]         = best_meta["url"]
            final["asset_match_score"] = round(best_score, 3)
            print(f"    Resolution : SUCCESS")
        else:
            final["asset_error"] = (
                f"no_match (best: '{best_meta['name']}', score: {best_score:.3f})"
            )
            print(f"    Resolution : FAILED (score below THRESHOLD_WEAK={THRESHOLD_WEAK})")

        print(f"    Final JSON :")
        for line in json.dumps(final, indent=6).splitlines():
            print(f"    {line}")

        total = llm_elapsed + embed_elapsed
        print(f"\n    Total time this run : {total:.2f}s  "
              f"(LLM {llm_elapsed:.2f}s + embed {embed_elapsed:.3f}s)")

    print(f"\n{SEP_THICK}")
    print(f"  All {runs} runs complete.")
    print(SEP_THICK)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detailed single-spawn pipeline trace.")
    parser.add_argument("--transcript", default=DEFAULT_TRANSCRIPT,
                        help="Voice transcript to trace (must be a spawn command)")
    parser.add_argument("--model",      default=MODEL_NAME,
                        help="LLM model name (must be pulled in Ollama)")
    parser.add_argument("--runs",       default=DEFAULT_RUNS, type=int,
                        help="Number of times to run the same transcript")
    args = parser.parse_args()

    run_trace(
        transcript=args.transcript,
        model=args.model,
        runs=args.runs,
    )
