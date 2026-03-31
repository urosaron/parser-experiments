"""
Synthetic asset library for RAG development and testing.

Each entry has:
  name        — display name used in the scene
  description — what gets embedded and searched (keep it rich with material/style/shape keywords)
  url         — CDN path that gets sent to the scene server after resolution

Replace with real CDN entries once the asset catalogue is finalised (see rag.md §7).
"""

ASSETS: list[dict] = [
    # ── Seating ────────────────────────────────────────────────────────────────
    {
        "name": "Wooden Chair",
        "description": "wooden chair four legs light oak finish dining seat",
        "url": "https://cdn.holodeck.com/assets/furniture/wooden_chair_v2.glb",
    },
    {
        "name": "Office Chair",
        "description": "office chair ergonomic mesh back adjustable height armrests swivel wheels",
        "url": "https://cdn.holodeck.com/assets/furniture/office_chair_v1.glb",
    },
    {
        "name": "Armchair",
        "description": "armchair upholstered fabric padded cushion wide seat lounge reading",
        "url": "https://cdn.holodeck.com/assets/furniture/armchair_v1.glb",
    },
    {
        "name": "Bar Stool",
        "description": "bar stool tall metal legs counter height footrest round seat",
        "url": "https://cdn.holodeck.com/assets/furniture/bar_stool_v1.glb",
    },
    # ── Tables ─────────────────────────────────────────────────────────────────
    {
        "name": "Oak Dining Table",
        "description": "dining table rectangular oak wood four legs large surface",
        "url": "https://cdn.holodeck.com/assets/furniture/oak_dining_table_v1.glb",
    },
    {
        "name": "Coffee Table",
        "description": "coffee table low rectangular glass top metal frame living room",
        "url": "https://cdn.holodeck.com/assets/furniture/coffee_table_v1.glb",
    },
    {
        "name": "Desk",
        "description": "writing desk flat surface computer workstation office wooden legs",
        "url": "https://cdn.holodeck.com/assets/furniture/desk_v1.glb",
    },
    # ── Lighting ───────────────────────────────────────────────────────────────
    {
        "name": "Floor Lamp",
        "description": "floor lamp tall standing metal pole shade ambient light living room",
        "url": "https://cdn.holodeck.com/assets/lighting/floor_lamp_v1.glb",
    },
    {
        "name": "Desk Lamp",
        "description": "desk lamp small table lamp adjustable arm reading light office",
        "url": "https://cdn.holodeck.com/assets/lighting/desk_lamp_v1.glb",
    },
    {
        "name": "Ceiling Light",
        "description": "ceiling light pendant hanging overhead fixture round diffuser",
        "url": "https://cdn.holodeck.com/assets/lighting/ceiling_light_v1.glb",
    },
    # ── Storage ────────────────────────────────────────────────────────────────
    {
        "name": "Bookshelf",
        "description": "bookshelf tall wooden shelving unit multiple shelves storage books",
        "url": "https://cdn.holodeck.com/assets/furniture/bookshelf_v1.glb",
    },
    {
        "name": "Cabinet",
        "description": "cabinet storage unit wooden doors hinged enclosed cupboard",
        "url": "https://cdn.holodeck.com/assets/furniture/cabinet_v1.glb",
    },
    {
        "name": "Wardrobe",
        "description": "wardrobe large tall clothing storage sliding doors bedroom",
        "url": "https://cdn.holodeck.com/assets/furniture/wardrobe_v1.glb",
    },
    # ── Soft furnishings ───────────────────────────────────────────────────────
    {
        "name": "Sofa",
        "description": "sofa three seat couch upholstered fabric cushions living room",
        "url": "https://cdn.holodeck.com/assets/furniture/sofa_v1.glb",
    },
    {
        "name": "Rug",
        "description": "rug carpet floor mat woven fabric rectangular patterned living room",
        "url": "https://cdn.holodeck.com/assets/decor/rug_v1.glb",
    },
    # ── Plants and decor ───────────────────────────────────────────────────────
    {
        "name": "Potted Plant",
        "description": "potted plant indoor houseplant green leaves ceramic pot",
        "url": "https://cdn.holodeck.com/assets/decor/potted_plant_v1.glb",
    },
    {
        "name": "Painting",
        "description": "painting framed wall art canvas picture decorative",
        "url": "https://cdn.holodeck.com/assets/decor/painting_v1.glb",
    },
    # ── Primitives / dev placeholders ─────────────────────────────────────────
    {
        "name": "Wooden Crate",
        "description": "wooden crate box storage container planks rough",
        "url": "https://cdn.holodeck.com/assets/props/wooden_crate_v1.glb",
    },
    {
        "name": "Metal Barrel",
        "description": "metal barrel cylindrical drum industrial storage container",
        "url": "https://cdn.holodeck.com/assets/props/metal_barrel_v1.glb",
    },
]
