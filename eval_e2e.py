"""
End-to-end eval: transcript → LLM parser → RAG → final command.

Tests the full pipeline in tandem. Each case starts with a raw voice transcript
(as it would arrive from Whisper) and checks that the final resolved command
contains the expected asset URL.

Run with:
    python eval_e2e.py
    python eval_e2e.py --model qwen3.5:4b
"""

import argparse
import json
import sys
import time

from rag.query import AssetResolver
from test_parser import MODEL_NAME, parse_and_resolve

# ── Shared context used across all cases ──────────────────────────────────────
DEFAULT_USER = {
    "id": "user_1",
    "position": {"x": 0, "y": 1.7, "z": 3},
    "look_direction": {"x": 0, "y": 0, "z": -1},
    "point_target": None,
}

EMPTY_SCENE = []

# A scene with a couple of reference objects, used by positional spawn cases
SCENE_WITH_REFS = [
    {
        "id": "server_w001",
        "name": "Window Frame",
        "metadata": {"type": "plane", "label": "Window Frame"},
        "position": {"x": 0, "y": 1, "z": -5},
    },
    {
        "id": "server_t001",
        "name": "Oak Table",
        "metadata": {"type": "table", "label": "Oak Table"},
        "position": {"x": 2, "y": 0, "z": 0},
    },
]

# ── Test cases ────────────────────────────────────────────────────────────────
# Fields:
#   id              — unique name for the case
#   transcript      — raw voice input as it arrives from Whisper
#   scene           — scene graph sent to the parser
#   expected_asset  — asset name the RAG should resolve to
#   expected_cmd    — top-level "command" field expected from the parser
#
# Notes on expected_asset:
#   For non-spawn commands (edit/delete/none), set expected_asset to None.
#   For spawn commands, set to the asset name string in assets.py.

CASES = [
    # ── Clean spawns — no positional context ──────────────────────────────────
    {
        "id": "spawn_wooden_chair",
        "transcript": "spawn a wooden chair",
        "scene": EMPTY_SCENE,
        "expected_cmd": "spawn",
        "expected_asset": "Wooden Chair",
    },
    {
        "id": "spawn_floor_lamp",
        "transcript": "add a floor lamp",
        "scene": EMPTY_SCENE,
        "expected_cmd": "spawn",
        "expected_asset": "Floor Lamp",
    },
    {
        "id": "spawn_sofa",
        "transcript": "place a sofa here",
        "scene": EMPTY_SCENE,
        "expected_cmd": "spawn",
        "expected_asset": "Sofa",
    },
    {
        "id": "spawn_bookshelf",
        "transcript": "add a bookshelf",
        "scene": EMPTY_SCENE,
        "expected_cmd": "spawn",
        "expected_asset": "Bookshelf",
    },
    {
        "id": "spawn_potted_plant",
        "transcript": "put a potted plant here",
        "scene": EMPTY_SCENE,
        "expected_cmd": "spawn",
        "expected_asset": "Potted Plant",
    },
    # ── Spawns with positional context — parser must strip it from asset_query ─
    {
        "id": "spawn_chair_near_window",
        "transcript": "spawn a wooden chair near the window",
        "scene": SCENE_WITH_REFS,
        "expected_cmd": "spawn",
        "expected_asset": "Wooden Chair",
    },
    {
        "id": "spawn_lamp_corner",
        "transcript": "put a tall floor lamp in the corner",
        "scene": EMPTY_SCENE,
        "expected_cmd": "spawn",
        "expected_asset": "Floor Lamp",
    },
    {
        "id": "spawn_desk_by_table",
        "transcript": "place a desk next to the table",
        "scene": SCENE_WITH_REFS,
        "expected_cmd": "spawn",
        "expected_asset": "Desk",
    },
    # ── Synonym / paraphrase spawns ───────────────────────────────────────────
    {
        "id": "spawn_oak_seat_synonym",
        "transcript": "bring in an oak dining seat",
        "scene": EMPTY_SCENE,
        "expected_cmd": "spawn",
        "expected_asset": "Wooden Chair",
    },
    {
        "id": "spawn_couch_synonym",
        "transcript": "I want a three seater couch over there",
        "scene": EMPTY_SCENE,
        "expected_cmd": "spawn",
        "expected_asset": "Sofa",
    },
    {
        "id": "spawn_workstation_synonym",
        "transcript": "add a computer workstation",
        "scene": EMPTY_SCENE,
        "expected_cmd": "spawn",
        "expected_asset": "Desk",
    },
    # ── Non-spawn commands — RAG should not be invoked ────────────────────────
    {
        "id": "edit_move",
        "transcript": "move the oak table a bit to the left",
        "scene": SCENE_WITH_REFS,
        "expected_cmd": "edit",
        "expected_asset": None,
    },
    {
        "id": "no_command",
        "transcript": "what do you think of this layout?",
        "scene": EMPTY_SCENE,
        "expected_cmd": "none",
        "expected_asset": None,
    },
]


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_case(case: dict, result: dict) -> dict:
    cmd_ok = result.get("command") == case["expected_cmd"]
    asset_ok = True  # default for non-spawn

    if case["expected_asset"] is not None:
        # Spawn: check asset_url was resolved and points to the expected asset
        url = result.get("asset_url", "")
        # URL contains the asset slug; derive name from assets.py for comparison
        from rag.assets import ASSETS
        matched_name = next(
            (a["name"] for a in ASSETS if a["url"] == url), None
        )
        asset_ok = matched_name == case["expected_asset"]
    elif result.get("command") == "spawn":
        # Expected non-spawn but got spawn — already fails on cmd_ok
        asset_ok = False

    return {
        "cmd_ok": cmd_ok,
        "asset_ok": asset_ok,
        "pass": cmd_ok and asset_ok,
    }


# ── Runner ────────────────────────────────────────────────────────────────────

def run(model: str) -> None:
    print(f"Model   : {model}")
    print(f"Cases   : {len(CASES)}")
    print("Loading asset resolver...")
    resolver = AssetResolver()
    print()

    rows = []

    for case in CASES:
        t0 = time.perf_counter()
        result = parse_and_resolve(
            transcript=case["transcript"],
            user_context=DEFAULT_USER,
            scene=case["scene"],
            resolver=resolver,
        )
        elapsed = time.perf_counter() - t0

        scores = score_case(case, result)

        asset_query = result.get("asset_query", "")   # only present if RAG failed
        asset_url   = result.get("asset_url", "")
        asset_error = result.get("asset_error", "")
        score_val   = result.get("asset_match_score", "")
        got_cmd     = result.get("command", "error")

        # Derive resolved asset name from URL
        if asset_url:
            from rag.assets import ASSETS
            resolved_name = next(
                (a["name"] for a in ASSETS if a["url"] == asset_url), asset_url
            )
        elif asset_error:
            resolved_name = f"ERROR: {asset_error}"
        elif asset_query:
            resolved_name = f"UNRESOLVED: {asset_query}"
        else:
            resolved_name = "-"

        status = "PASS" if scores["pass"] else (
            "CMD_FAIL" if not scores["cmd_ok"] else "ASSET_FAIL"
        )

        rows.append({
            "id": case["id"],
            "transcript": case["transcript"],
            "expected_cmd": case["expected_cmd"],
            "got_cmd": got_cmd,
            "expected_asset": case["expected_asset"] or "-",
            "resolved_asset": resolved_name,
            "score": f"{score_val:.3f}" if isinstance(score_val, float) else "-",
            "elapsed": f"{elapsed:.1f}s",
            "status": status,
            "full_result": result,
        })

        marker = "OK" if scores["pass"] else "FAIL"
        print(f"  [{marker}] {case['id']:<30}  cmd={got_cmd:<8}  asset={resolved_name}  ({elapsed:.1f}s)")

    # Summary
    passed = sum(1 for r in rows if r["status"] == "PASS")
    total  = len(rows)
    print(f"\n{'-' * 70}")
    print(f"Results: {passed}/{total} passed")

    # Print full JSON for each case for inspection
    print(f"\n{'-' * 70}")
    print("Full outputs:\n")
    for row in rows:
        print(f"  {row['id']}")
        print(f"  Transcript : {row['transcript']}")
        print(f"  Result     : {json.dumps(row['full_result'], indent=4)}")
        print()

    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL_NAME)
    args = parser.parse_args()

    # Patch model name if overridden
    if args.model != MODEL_NAME:
        import test_parser
        test_parser.MODEL_NAME = args.model

    run(args.model)
