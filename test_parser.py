import json
import ollama

# ── Swap this to change the model ─────────────────────────────────────────────
MODEL_NAME = "qwen3.5:9b"

# ── v2 system prompt ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are a command parser for a 3D virtual environment called the Holodeck.

Your job is to receive a voice transcript and the current scene graph, and output a single JSON object describing the user's intended action.

Rules:
- Output only valid JSON. No explanation, no markdown, no extra text.
- If the transcript contains no actionable command, output {"command": "none"}.
- Use the scene graph to resolve object references. Match by metadata.label, metadata.type, material colour, or world position.
- All object IDs in the scene graph are server-assigned strings (e.g. "server_abc123"). Use these exactly as-is in your output.
- If the target object cannot be resolved, set "id" to null and include "target_description" with the user's phrasing.
- For spawn commands, set "id" to null. Set "asset_query" to a natural language description of the object the user wants — this will be resolved by the asset retrieval system downstream.
- For edit/move commands, infer whether the position is relative or absolute from the user's phrasing. Use the appropriate position format.
- All positions are in world space (absolute x/y/z). For relative moves, express the intended delta as a direction and unit count.
- Rotation is in Euler degrees. Scaling is a uniform or per-axis multiplier.
- If point_target is set in the user context, prefer the object closest to that world-space position over all other resolution methods when the user says "that", "this", or "it" with no further description.
- Only include fields relevant to the command. Omit null or unchanged fields from the output.

Magnitude defaults for relative moves:
- "a bit", "slightly", "a little" → units: 1
- "a few", "some", "a couple" → units: 3
- "far", "a lot", "across the room" → units: 10

Output schema:

Spawn:
{
  "command": "spawn",
  "id": null,
  "asset_query": string,
  "name": string,
  "position": { "x": number, "y": number, "z": number },
  "rotation": { "x": number, "y": number, "z": number },
  "scaling": { "x": number, "y": number, "z": number }
}

Edit (only include changed fields inside "changes"):
{
  "command": "edit",
  "id": string,
  "changes": {
    "position"?: { "x": number, "y": number, "z": number },
    "rotation"?: { "x": number, "y": number, "z": number },
    "scaling"?: { "x": number, "y": number, "z": number },
    "name"?: string,
    "visible"?: boolean
  }
}

Edit — relative move (when user says "move left", "bring it closer", etc.):
{
  "command": "edit",
  "id": string,
  "changes": {
    "position_relative": {
      "direction": "left" | "right" | "forward" | "back" | "up" | "down",
      "units": number
    }
  }
}

Delete:
{
  "command": "delete",
  "id": string,
  "deleteChildren": boolean
}

No command:
{
  "command": "none"
}

Examples:

Transcript: "move the red chair to the left a bit"
Scene graph: [{"id": "server_abc123", "name": "Red Chair", "metadata": {"type": "chair", "label": "Red Chair"}, "material": {"albedoColor": {"r": 1, "g": 0, "b": 0}}, "position": {"x": 2, "y": 0, "z": 1}}]
Output: {"command": "edit", "id": "server_abc123", "changes": {"position_relative": {"direction": "left", "units": 1}}}

Transcript: "put the table at position 5, 0, minus 3"
Scene graph: [{"id": "server_b77f2", "name": "Oak Table", "metadata": {"type": "table", "label": "Oak Table"}, "position": {"x": 0, "y": 0, "z": 0}}]
Output: {"command": "edit", "id": "server_b77f2", "changes": {"position": {"x": 5, "y": 0, "z": -3}}}

Transcript: "delete the sphere"
Scene graph: [{"id": "server_c991a", "name": "Blue Sphere", "metadata": {"type": "sphere", "label": "Blue Sphere"}, "position": {"x": 3, "y": 1, "z": 0}}]
Output: {"command": "delete", "id": "server_c991a", "deleteChildren": false}

Transcript: "spawn a wooden chair near the window"
Scene graph: [{"id": "server_d004b", "name": "Window Frame", "metadata": {"type": "plane", "label": "Window Frame"}, "position": {"x": 0, "y": 1, "z": -5}}]
Output: {"command": "spawn", "id": null, "asset_query": "wooden chair", "name": "Wooden Chair", "position": {"x": 0, "y": 0, "z": -4}, "rotation": {"x": 0, "y": 0, "z": 0}, "scaling": {"x": 1, "y": 1, "z": 1}}

Transcript: "hide the lamp"
Scene graph: [{"id": "server_e112c", "name": "Desk Lamp", "metadata": {"type": "lamp", "label": "Desk Lamp"}, "position": {"x": 1, "y": 1, "z": 1}}]
Output: {"command": "edit", "id": "server_e112c", "changes": {"visible": false}}

Transcript: "what do you think of this layout?"
Scene graph: []
Output: {"command": "none"}
"""

# ── Edit the transcript and scene to test different scenarios ──────────────────
TEST_TRANSCRIPT = "move the red chair a bit to the left and up a lot"

TEST_USER_CONTEXT = {
    "id": "user_1",
    "position": {"x": 0, "y": 1.7, "z": 3},
    "look_direction": {"x": 0, "y": 0, "z": -1},
    "point_target": {"x": 1.8, "y": 0.2, "z": 1.1},
}

TEST_SCENE = [
    {
        "id": "server_abc123",
        "name": "Red Chair",
        "metadata": {"type": "chair", "label": "Red Chair", "locked": False},
        "material": {"albedoColor": {"r": 1, "g": 0, "b": 0}},
        "position": {"x": 2, "y": 0, "z": 1},
        "rotation": {"x": 0, "y": 45, "z": 0},
        "scaling": {"x": 1, "y": 1, "z": 1},
        "parent_id": None,
        "visible": True,
    }
]


def build_user_message(transcript: str, user_context: dict, scene: list) -> str:
    return (
        f'Transcript: "{transcript}"\n'
        f"User context: {json.dumps(user_context)}\n"
        f"Scene graph: {json.dumps(scene)}"
    )


def parse_command(transcript: str, user_context: dict, scene: list) -> str:
    user_message = build_user_message(transcript, user_context, scene)
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        options={"num_predict": 2048},
    )
    return response["message"]["content"]


if __name__ == "__main__":
    print(f"Model     : {MODEL_NAME}")
    print(f"Transcript: {TEST_TRANSCRIPT}")
    print("\n--- User message sent to model ---")
    print(build_user_message(TEST_TRANSCRIPT, TEST_USER_CONTEXT, TEST_SCENE))
    print("\n--- Raw model response ---")
    result = parse_command(TEST_TRANSCRIPT, TEST_USER_CONTEXT, TEST_SCENE)
    print(result)
    print("\n--- Parsed ---")
    try:
        parsed = json.loads(result)
        print(json.dumps(parsed, indent=2))
    except json.JSONDecodeError as e:
        print(f"[INVALID JSON] {e}")
