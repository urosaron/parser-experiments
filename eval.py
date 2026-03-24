"""
eval.py — Baseline scorer for the Holodeck parser.

Runs every case in test_cases.py through the model and reports:
  - valid_json      : output parses as JSON without error
  - correct_command : "command" field matches expected
  - correct_id      : "id" field matches expected (including None / null)

Usage:
    python eval.py [--model MODEL_NAME] [--category CATEGORY] [--case CASE_ID]

Examples:
    python eval.py
    python eval.py --model qwen3.5:14b
    python eval.py --category relative_move
    python eval.py --case rel_move_left_bit
"""

import argparse
import json
import time

import ollama

from test_cases import CASES
from test_parser import SYSTEM_PROMPT, build_user_message

# ── Column widths for the results table ───────────────────────────────────────
COL_ID = 30
COL_CAT = 22
COL_JSON = 10
COL_CMD = 10
COL_ID_COL = 10
COL_MS = 8

PASS = "PASS"
FAIL = "FAIL"


def run_case(case: dict, model: str) -> dict:
    user_msg = build_user_message(case["transcript"], case["user"], case["scene"])
    t0 = time.monotonic()
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        options={"num_predict": 2048},
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    raw = response["message"]["content"].strip()

    # Strip markdown fences if the model wraps output despite instructions
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        parsed = json.loads(raw)
        valid_json = True
    except json.JSONDecodeError:
        parsed = {}
        valid_json = False

    expected = case["expected"]
    correct_command = parsed.get("command") == expected.get("command")
    # id check only applies to cases where expected has an "id" key
    if "id" in expected:
        correct_id = parsed.get("id") == expected["id"]
    else:
        correct_id = None  # not evaluated for this case

    return {
        "id": case["id"],
        "category": case["category"],
        "valid_json": valid_json,
        "correct_command": correct_command,
        "correct_id": correct_id,
        "raw": raw,
        "parsed": parsed,
        "elapsed_ms": elapsed_ms,
    }


def fmt(value) -> str:
    if value is None:
        return " N/A "
    return PASS if value else FAIL


def print_header():
    print(
        f"{'Case':<{COL_ID}} {'Category':<{COL_CAT}} "
        f"{'JSON':>{COL_JSON}} {'Command':>{COL_CMD}} "
        f"{'ID':>{COL_ID_COL}} {'ms':>{COL_MS}}"
    )
    print("-" * (COL_ID + COL_CAT + COL_JSON + COL_CMD + COL_ID_COL + COL_MS + 5))


def print_row(r: dict):
    print(
        f"{r['id']:<{COL_ID}} {r['category']:<{COL_CAT}} "
        f"{fmt(r['valid_json']):>{COL_JSON}} {fmt(r['correct_command']):>{COL_CMD}} "
        f"{fmt(r['correct_id']):>{COL_ID_COL}} {r['elapsed_ms']:>{COL_MS}}"
    )


def print_summary(results: list):
    total = len(results)
    valid_json_count = sum(1 for r in results if r["valid_json"])
    correct_command_count = sum(1 for r in results if r["correct_command"])
    id_results = [r for r in results if r["correct_id"] is not None]
    correct_id_count = sum(1 for r in id_results if r["correct_id"])

    print()
    print("=" * (COL_ID + COL_CAT + COL_JSON + COL_CMD + COL_ID_COL + COL_MS + 5))
    print(f"Total cases : {total}")
    print(f"Valid JSON  : {valid_json_count}/{total}")
    print(f"Command     : {correct_command_count}/{total}")
    if id_results:
        print(f"ID          : {correct_id_count}/{len(id_results)}  (cases with expected id)")


def print_failures(results: list):
    failures = [
        r for r in results
        if not r["valid_json"] or not r["correct_command"]
        or (r["correct_id"] is not None and not r["correct_id"])
    ]
    if not failures:
        print("\nAll cases passed.")
        return
    print(f"\n── Failed cases ({len(failures)}) ────────────────────────────────")
    for r in failures:
        print(f"\n[{r['id']}]")
        issues = []
        if not r["valid_json"]:
            issues.append("invalid JSON")
        if not r["correct_command"]:
            issues.append("wrong command")
        if r["correct_id"] is not None and not r["correct_id"]:
            issues.append("wrong id")
        print(f"  Issues  : {', '.join(issues)}")
        print(f"  Raw out : {r['raw'][:200]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3.5:9b", help="Ollama model name")
    parser.add_argument("--category", default=None, help="Filter to a single category")
    parser.add_argument("--case", default=None, help="Run a single case by id")
    args = parser.parse_args()

    cases = CASES
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"No case found with id '{args.case}'")
            return
    elif args.category:
        cases = [c for c in cases if c["category"] == args.category]
        if not cases:
            print(f"No cases found in category '{args.category}'")
            return

    print(f"Model  : {args.model}")
    print(f"Cases  : {len(cases)}")
    print()
    print_header()

    results = []
    for case in cases:
        result = run_case(case, args.model)
        print_row(result)
        results.append(result)

    print_summary(results)
    print_failures(results)


if __name__ == "__main__":
    main()
