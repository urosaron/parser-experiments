"""
RAG retrieval eval — tests whether asset queries resolve to the expected asset.

Run with:
    python -m rag.eval_rag

Uses the live ChromaDB index (must have run `python -m rag.index` first).
"""

from rag.query import AssetResolver, THRESHOLD_STRONG, THRESHOLD_WEAK

# ── Test cases ────────────────────────────────────────────────────────────────
# Each entry: (query, expected_asset_name)
#
# All queries are written as asset_query would actually look coming out of the
# parser: short, context-free object descriptors (material + style + type).
# No positional phrases ("near the window", "for the corner") — those are
# resolved by the parser, not the RAG.
#
# Three groups:
#   A. Direct / near-exact  — query closely matches the stored description
#   B. Semantic synonyms    — different words, same meaning
#   C. Similar-asset pairs  — assets that are close neighbours; queries must
#                             carry enough signal to distinguish them

CASES: list[tuple[str, str]] = [
    # ── A. Direct / near-exact ────────────────────────────────────────────────
    ("wooden chair", "Wooden Chair"),
    ("office chair", "Office Chair"),
    ("floor lamp", "Floor Lamp"),
    ("desk lamp", "Desk Lamp"),
    ("oak dining table", "Oak Dining Table"),
    ("coffee table", "Coffee Table"),
    ("bar stool", "Bar Stool"),
    ("potted plant", "Potted Plant"),
    ("wooden bookshelf", "Bookshelf"),
    ("fabric sofa", "Sofa"),
    ("woven floor rug", "Rug"),
    ("large wardrobe", "Wardrobe"),
    ("wooden crate", "Wooden Crate"),
    ("metal barrel", "Metal Barrel"),

    # ── B. Semantic synonyms ──────────────────────────────────────────────────
    ("oak dining chair", "Wooden Chair"),          # material synonym
    ("light oak seat", "Wooden Chair"),            # partial description match
    ("ergonomic mesh office chair", "Office Chair"),
    ("upholstered lounge chair", "Armchair"),
    ("three seat fabric couch", "Sofa"),
    ("indoor ceramic pot plant", "Potted Plant"),
    ("framed canvas wall art", "Painting"),
    ("wooden plank storage box", "Wooden Crate"),
    ("cylindrical metal drum", "Metal Barrel"),
    ("tall wooden bookcase", "Bookshelf"),
    ("large bedroom wardrobe", "Wardrobe"),
    ("computer workstation desk", "Desk"),

    # ── C. Similar-asset pairs ────────────────────────────────────────────────
    # Floor lamp vs Desk Lamp — must carry tall/standing vs small/table signal
    ("tall standing pole lamp", "Floor Lamp"),
    ("small table reading lamp", "Desk Lamp"),
    ("overhead hanging pendant light", "Ceiling Light"),
    # Wooden Chair vs Armchair — chair type signal
    ("padded wide armchair", "Armchair"),
    ("counter height tall stool", "Bar Stool"),
    # Desk vs Coffee Table — surface height/purpose signal
    ("low glass living room table", "Coffee Table"),
    ("rectangular oak large dining table", "Oak Dining Table"),
]


def run_eval() -> None:
    print("Loading asset resolver...")
    resolver = AssetResolver()
    print(f"Index contains {resolver._collection.count()} assets.\n")

    header = f"{'Query':<45} {'Expected':<22} {'Got':<22} {'Score':>6}  {'Result'}"
    print(header)
    print("-" * len(header))

    passed = 0
    weak = 0
    failed = 0

    for query, expected_name in CASES:
        url, score, matched_name = resolver.resolve(query)

        correct = matched_name == expected_name
        tag = ""
        if url is None:
            tag = "MISS"
            failed += 1
        elif score < THRESHOLD_STRONG:
            tag = "WEAK" if correct else "WRONG"
            weak += 1 if correct else 0
            failed += 0 if correct else 1
        else:
            tag = "OK" if correct else "WRONG"
            passed += 1 if correct else 0
            failed += 0 if correct else 1

        score_str = f"{score:.3f}"
        print(
            f"{query:<45} {expected_name:<22} {matched_name:<22} {score_str:>6}  {tag}"
        )

    total = len(CASES)
    print(f"\n{'-' * 80}")
    print(f"Results: {passed}/{total} passed  |  {weak} weak matches  |  {failed} failed")
    print(
        f"Thresholds: strong >= {THRESHOLD_STRONG}  |  weak >= {THRESHOLD_WEAK}  |  miss < {THRESHOLD_WEAK}"
    )


if __name__ == "__main__":
    run_eval()
