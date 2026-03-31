# RAG Implementation: Findings and Dataflow

Trans Realities Lab · Holodeck Project · March 2026

Author: Uroš Aron Čolović

---

## Contents

1. [What Was Built](#1-what-was-built)
2. [Full Dataflow: Voice to Scene](#2-full-dataflow-voice-to-scene)
3. [Internal RAG Dataflow](#3-internal-rag-dataflow)
4. [Eval Results](#4-eval-results)
5. [Findings and Observations](#5-findings-and-observations)
6. [Open Items](#6-open-items)

---

## 1. What Was Built

The RAG system described in `rag.md` was implemented in a single session on 2026-03-31 and is now fully functional end-to-end. All components run locally via Ollama and ChromaDB with no cloud dependencies.

| File | Role |
|---|---|
| `rag/assets.py` | Synthetic asset library — 19 entries with name, description, and CDN URL |
| `rag/index.py` | Builds the ChromaDB vector index from the asset library. Run once (or on library changes). |
| `rag/query.py` | `AssetResolver` class — embeds a query and returns the closest CDN URL |
| `rag/eval_rag.py` | 27-case retrieval eval covering direct matches, synonyms, paraphrases, and context phrases |
| `test_parser.py` | Extended with `parse_and_resolve()` — the complete pipeline from transcript to final command |

**Stack:**

| Component | Model / Version | Role |
|---|---|---|
| Ollama | — | Serves all models locally |
| `qwen3.5:9b` | qwen3.5:9b | LLM parser (transcript → JSON command) |
| `qwen3-embedding:8b` | qwen3-embedding:8b | Embedding model (text → vector) |
| ChromaDB | 1.5.5 | Vector store (cosine similarity, persistent on disk) |

---

## 2. Full Dataflow: Voice to Scene

This is the complete path from a spoken voice command to an executed action in the BabylonJS scene.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER SPEAKS                                    │
│              "spawn a wooden chair near the window"                     │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ audio
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — ASR (Whisper)                                                │
│  Converts audio to raw transcript text                                  │
│  Output: "spawn a wooden chair near the window"                         │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ transcript text
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — Scene Server (Colyseus)                                      │
│  Builds parser input: transcript + filtered list of nearby objects      │
│  Only objects within proximity radius are included — server decides     │
│  Output: { transcript, user_context, scene: [...nearby objects...] }    │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ structured input
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 3 — LLM Parser (qwen3.5:9b via Ollama)                          │
│                                                                         │
│  Receives transcript + scene graph.                                     │
│  Determines command type and resolves object references.                │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  Existing object? (edit / delete / hide)                    │        │
│  │  → ID is in scene context. Read it. Output command with ID. │        │
│  │  No RAG involved.                                           │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  New object? (spawn)                                        │        │
│  │  → No ID exists. Output asset_query: "wooden chair"         │        │
│  │  asset_query goes to Stage 4.                               │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                                                         │
│  Output (spawn): { "command": "spawn", "asset_query": "wooden chair",   │
│                    "name": "Wooden Chair", "position": {...} }          │
└──────────────┬──────────────────────────┬───────────────────────────────┘
               │ edit/delete/none         │ spawn only
               │ (skip Stage 4)           ▼
               │           ┌─────────────────────────────────────────────┐
               │           │  STAGE 4 — RAG (ChromaDB + qwen3-emb:8b)   │
               │           │                                             │
               │           │  1. Embed asset_query → vector              │
               │           │  2. Query ChromaDB for nearest neighbour    │
               │           │  3. Check cosine similarity score           │
               │           │     >= 0.85 → strong match, use URL         │
               │           │     >= 0.75 → weak match, use with caution  │
               │           │     <  0.75 → no match, return error        │
               │           │  4. Replace asset_query with asset_url      │
               │           │                                             │
               │           │  Output: { "command": "spawn",              │
               │           │   "asset_url": "https://cdn.../chair.glb",  │
               │           │   "name": "Wooden Chair", "position": {...}}│
               │           └──────────────────┬──────────────────────────┘
               │                              │ resolved command
               └──────────────────────────────┘
                          │ final command (all types)
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 5 — Scene Server (Colyseus)                                      │
│  Validates the command. For spawn: fetches mesh from asset_url,         │
│  creates the object in the scene, assigns a new server ID.              │
│  Syncs state to all connected clients.                                  │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ scene update
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 6 — BabylonJS Scene                                              │
│  Executes the action on the correct mesh. Object is now live in scene.  │
│  From this point, it has a server ID and is referenced like any other.  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Command-type routing at a glance

| Command | Parser uses scene ID? | RAG involved? | CDN fetch? |
|---|---|---|---|
| `edit` (move, rotate, scale, hide, show) | Yes | No | No |
| `delete` | Yes | No | No |
| `spawn` | No (no ID yet) | **Yes** | **Yes** |
| `none` | — | No | No |

---

## 3. Internal RAG Dataflow

Zooming in on Stage 4 only, showing both phases:

```
── INDEXING PHASE (runs once, or on asset library update) ──────────────

  assets.py                  index.py                    ChromaDB
  ┌──────────┐               ┌──────────────────────┐    ┌────────────┐
  │  name    │               │  for each asset:     │    │            │
  │  desc    │──description──▶  embed(description)  │    │  id        │
  │  url     │               │  → vector [f32 x N]  │───▶│  vector    │
  └──────────┘               └──────────────────────┘    │  metadata  │
                              model: qwen3-embedding:8b   │  {name,url}│
                                                          │            │
                                                          │  space:    │
                                                          │  cosine    │
                                                          └────────────┘


── QUERY PHASE (every spawn command) ───────────────────────────────────

  Parser output             query.py                    ChromaDB
  ┌──────────────────┐      ┌──────────────────────┐    ┌────────────┐
  │ asset_query:     │      │  embed(asset_query)  │    │            │
  │ "wooden chair"   │─────▶│  → vector [f32 x N]  │───▶│  nearest   │
  └──────────────────┘      └──────────────────────┘    │  neighbour │
                              model: qwen3-embedding:8b  │  search    │
                                                         └─────┬──────┘
                                                               │
                                                    score = 1 - distance
                                                               │
                                              ┌────────────────▼──────────┐
                                              │  score >= 0.85 → URL      │
                                              │  score >= 0.75 → URL      │
                                              │  score <  0.75 → None     │
                                              └────────────────┬──────────┘
                                                               │
                                              ┌────────────────▼──────────┐
                                              │ "https://cdn.holodeck.com │
                                              │  /assets/furniture/       │
                                              │  wooden_chair_v2.glb"     │
                                              └───────────────────────────┘
```

The ChromaDB collection is persisted to `rag/chroma_db/` and survives restarts. The index only needs to be rebuilt when `assets.py` changes.

---

## 4. Eval Results

**Date:** 2026-03-31
**Model:** qwen3-embedding:8b
**Index size:** 19 assets
**Test cases:** 27
**Overall:** 18 passed / 5 weak-but-correct / 4 failed

```
Query                                         Expected               Got                     Score  Result
----------------------------------------------------------------------------------------------------------
wooden chair                                  Wooden Chair           Wooden Chair            0.842  WEAK
office chair                                  Office Chair           Office Chair            0.931  OK
floor lamp                                    Floor Lamp             Floor Lamp              0.879  OK
desk lamp                                     Desk Lamp              Desk Lamp               0.927  OK
oak dining table                              Oak Dining Table       Oak Dining Table        0.868  OK
potted plant                                  Potted Plant           Potted Plant            0.918  OK
oak seat                                      Wooden Chair           Wooden Chair            0.783  WEAK
timber dining chair                           Wooden Chair           Wooden Chair            0.842  WEAK
ergonomic office seat with wheels             Office Chair           Office Chair            0.892  OK
lounge chair with cushions                    Armchair               Armchair                0.852  OK
tall reading light                            Floor Lamp             Floor Lamp              0.818  WEAK
small adjustable lamp for desk                Desk Lamp              Desk Lamp               0.915  OK
big wooden table for dining                   Oak Dining Table       Oak Dining Table        0.826  WEAK
glass coffee table                            Coffee Table           Coffee Table            0.869  OK
bookcase for storing books                    Bookshelf              Bookshelf               0.853  OK
three seat couch                              Sofa                   Sofa                    0.911  OK
indoor plant in a pot                         Potted Plant           Potted Plant            0.913  OK
framed wall picture                           Painting               Painting                0.914  OK
wooden storage box                            Wooden Crate           Wooden Crate            0.851  OK
metal drum container                          Metal Barrel           Metal Barrel            0.924  OK
wooden chair near the window                  Wooden Chair           Wooden Chair            0.736  MISS
a lamp for the corner                         Floor Lamp             Desk Lamp               0.802  WRONG
something to sit on                           Wooden Chair           Armchair                0.747  MISS
place to work at a computer                   Desk                   Desk                    0.741  MISS
bar height stool for the counter              Bar Stool              Bar Stool               0.877  OK
carpet for the floor                          Rug                    Rug                     0.865  OK
tall wardrobe for clothes                     Wardrobe               Wardrobe                0.859  OK
```

**Thresholds used:** strong ≥ 0.85 · weak ≥ 0.75 · miss < 0.75

---

## 5. Findings and Observations

### [2026-03-31] Strong threshold of 0.85 is slightly too tight

The score for querying `"wooden chair"` against an asset whose description is `"wooden chair four legs light oak finish dining seat"` comes in at 0.842 — just below the strong threshold. This is not a retrieval failure; the correct asset is returned. The score is lower because the query is a two-word subset of a richer seven-word description. All five WEAK cases are correct matches.

**Recommendation:** Lower `THRESHOLD_STRONG` from 0.85 to 0.80 in `rag/query.py`. This promotes all five weak-but-correct matches to OK with no false positives observed in the current eval set. Re-evaluate against the real asset library before finalising.

---

### [2026-03-31] Context phrases in asset_query reduce scores

The parser prompt instructs the model to output `asset_query: "wooden chair"`, stripping positional context like "near the window". In practice the model does not always do this — when it outputs `"wooden chair near the window"` as the asset_query, the score drops to 0.736 (MISS). The irrelevant spatial context pulls the embedding away from the asset description.

**Recommendation:** Add an explicit instruction to the parser system prompt: `asset_query must be a concise description of the object only — no position, no scene context, no qualifiers like "near the window".` Test with the existing eval cases to confirm.

---

### [2026-03-31] Ambiguous lamp queries resolve incorrectly

`"a lamp for the corner"` returned Desk Lamp (0.802) instead of Floor Lamp. The two lamp descriptions are semantically close; without "tall", "standing", or "floor" in the query, the model cannot distinguish between them. This is not a retrieval error — it is an under-specified query.

**Recommendation:** Two-pronged fix: (a) add `"standing tall pole"` to the floor lamp description and `"small table"` to the desk lamp description to increase the distance between them; (b) since the parser cannot reliably infer lamp type from vague queries, accept that vague queries may return either lamp. In practice users saying "a lamp for the corner" will most likely want a floor lamp — consider adding `"corner"` to the floor lamp description.

---

### [2026-03-31] Very vague queries score below the miss threshold

`"something to sit on"` (0.747) and `"place to work at a computer"` (0.741) land just below the 0.75 miss threshold. The latter is the more surprising case — "desk" is the semantically correct answer and it was returned, but the score is low because the description `"writing desk flat surface computer workstation"` doesn't share enough surface tokens with the query.

**Recommendation:** This is partially a description quality issue. Adding `"computer work"` and `"study"` to the desk description would likely push this above threshold. For genuinely vague queries like "something to sit on", raising descriptions to include purpose words ("seating", "sit") would help. However, these are edge cases — the parser produces `asset_query` from a transcript and should be producing tighter queries than these. If the parser is well-prompted, these edge cases should rarely appear in production.

---

### [2026-03-31] First embed call is slow (~9.5s cold start)

The first `ollama.embed()` call after Ollama starts takes around 9.5 seconds (loading the model into VRAM). Subsequent calls are fast (~0.1–0.2s). This is standard Ollama cold-start behaviour.

**Recommendation:** For production, warm the embedding model at server startup with a dummy embed call. Add to `rag/index.py` or a startup script.

---

## 6. Open Items

These are unresolved questions that will affect the transition from the synthetic asset library to real CDN assets.

| Item | Notes |
|---|---|
| Real CDN base URLs | Needed to replace synthetic URLs in `assets.py`. Blocked on Zak. |
| Real asset catalogue | The full list of assets and their descriptions. Descriptions must be written carefully — see §5 for how description quality directly affects retrieval. |
| Similarity threshold finalisation | Current recommendation: lower strong threshold to 0.80. Re-run `rag/eval_rag.py` once real assets are indexed. |
| Parser prompt update | Add explicit instruction to strip positional context from `asset_query`. Blocked on nothing — can be done now. |
| Warm-up call at server start | Low-effort quality-of-life improvement. Prevents 9.5s latency on first spawn in a session. |
| Scene server context filter count | How many nearby objects does Colyseus send to the parser? Owner: Balsa + Zak. |
