"""
Asset catalogue for the Holodeck RAG system.

Each entry has:
  name        — display name used in the scene
  description — what gets embedded and searched (keep it rich with material/style/shape keywords)
  url         — the asset URL returned to the scene after RAG resolution

URLs are constructed from ASSET_BASE_URL (set via environment variable or .env)
and a per-asset key. This means only ASSET_BASE_URL needs to change when moving
between machines (laptop → company PC).

  Laptop     : ASSET_BASE_URL=http://127.0.0.1:9000
  Company PC : ASSET_BASE_URL=http://<LAN-IP>:9000

Assets marked with a real MinIO key are live and fetchable. The remaining entries
use placeholder keys — they resolve correctly through RAG but the URL will 404
until matching .glb files are uploaded to the bucket.
"""

import os

ASSET_BASE_URL = os.environ.get("ASSET_BASE_URL", "http://127.0.0.1:9000").rstrip("/")
BUCKET = "holodeck-assets"


def _url(key: str) -> str:
    return f"{ASSET_BASE_URL}/{BUCKET}/{key}"


ASSETS: list[dict] = [
    # ── Seating ────────────────────────────────────────────────────────────────
    {
        "name": "Wooden Chair",
        "description": "wooden chair four legs light oak finish dining seat",
        "url": _url("furniture/sheen_chair.glb"),  # SheenChair from Khronos samples
    },
    {
        "name": "Office Chair",
        "description": "office chair ergonomic mesh back adjustable height armrests swivel wheels",
        "url": _url("furniture/office_chair.glb"),
    },
    {
        "name": "Armchair",
        "description": "armchair upholstered fabric padded cushion wide seat lounge reading",
        "url": _url("furniture/sheen_chair.glb"),  # placeholder — closest available asset
    },
    {
        "name": "Bar Stool",
        "description": "bar stool tall metal legs counter height footrest round seat",
        "url": _url("furniture/bar_stool.glb"),
    },
    # ── Tables ─────────────────────────────────────────────────────────────────
    {
        "name": "Oak Dining Table",
        "description": "dining table rectangular oak wood four legs large surface",
        "url": _url("furniture/oak_dining_table.glb"),
    },
    {
        "name": "Coffee Table",
        "description": "coffee table low rectangular glass top metal frame living room",
        "url": _url("furniture/coffee_table.glb"),
    },
    {
        "name": "Desk",
        "description": "writing desk flat surface computer workstation office wooden legs",
        "url": _url("furniture/desk.glb"),
    },
    # ── Lighting ───────────────────────────────────────────────────────────────
    {
        "name": "Floor Lamp",
        "description": "floor lamp tall standing metal pole shade ambient light living room",
        "url": _url("lighting/lantern.glb"),  # Lantern from Khronos samples
    },
    {
        "name": "Desk Lamp",
        "description": "desk lamp small table lamp adjustable arm reading light office",
        "url": _url("lighting/lantern.glb"),  # placeholder — closest available asset
    },
    {
        "name": "Ceiling Light",
        "description": "ceiling light pendant hanging overhead fixture round diffuser",
        "url": _url("lighting/ceiling_light.glb"),
    },
    # ── Storage ────────────────────────────────────────────────────────────────
    {
        "name": "Bookshelf",
        "description": "bookshelf tall wooden shelving unit multiple shelves storage books",
        "url": _url("furniture/bookshelf.glb"),
    },
    {
        "name": "Cabinet",
        "description": "cabinet storage unit wooden doors hinged enclosed cupboard",
        "url": _url("furniture/cabinet.glb"),
    },
    {
        "name": "Wardrobe",
        "description": "wardrobe large tall clothing storage sliding doors bedroom",
        "url": _url("furniture/wardrobe.glb"),
    },
    # ── Soft furnishings ───────────────────────────────────────────────────────
    {
        "name": "Sofa",
        "description": "sofa three seat couch upholstered fabric cushions living room",
        "url": _url("furniture/sofa.glb"),  # GlamVelvetSofa from Khronos samples
    },
    {
        "name": "Rug",
        "description": "rug carpet floor mat woven fabric rectangular patterned living room",
        "url": _url("decor/rug.glb"),
    },
    # ── Plants and decor ───────────────────────────────────────────────────────
    {
        "name": "Potted Plant",
        "description": "potted plant indoor houseplant green leaves ceramic pot",
        "url": _url("decor/avocado.glb"),  # Avocado from Khronos samples (stand-in for plant)
    },
    {
        "name": "Painting",
        "description": "painting framed wall art canvas picture decorative",
        "url": _url("decor/painting.glb"),
    },
    # ── Primitives / dev placeholders ─────────────────────────────────────────
    {
        "name": "Wooden Crate",
        "description": "wooden crate box storage container planks rough",
        "url": _url("props/wooden_crate.glb"),
    },
    {
        "name": "Metal Barrel",
        "description": "metal barrel cylindrical drum industrial storage container",
        "url": _url("props/duck.glb"),  # Duck from Khronos samples (stand-in for round prop)
    },
]
