# Holodeck AI Parser — Project Context for Cursor

## What this project is

This is the AI pipeline for the **Holodeck**, a web-based shared 3D virtual environment built with BabylonJS. Users interact with the scene using voice commands. The pipeline converts voice input into structured scene commands.

The stack is:
- **whispercpp** — speech-to-text (ASR), already selected and integrated
- **Qwen** — language model for the parser (running locally via ollama)
- **Parser** — the component we are currently building

The parser is a prompted LLM baseline. No fine-tuning yet. The goal right now is a working proof of concept that takes a voice transcript + scene snapshot and returns a valid command JSON.

---

## Current task

Build and test the **prompted baseline parser** using Qwen running locally. The parser receives a JSON request and returns a single JSON command object. Everything runs server-side.

---

## System prompt (v2 — current)

```
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
```

---

## Input format (frontend → AI server)

This is the JSON body the frontend sends per request. Agreed for v1 — shared with Balsa and Zak for confirmation but not yet formally ratified.

```json
{
  "transcript": "move that chair a bit to the left",

  "user": {
    "id": "user_1",
    "position": { "x": 0, "y": 1.7, "z": 3 },
    "look_direction": { "x": 0, "y": 0, "z": -1 },
    "point_target": { "x": 1.8, "y": 0.2, "z": 1.1 }
  },

  "scene": [
    {
      "id": "server_abc123",
      "name": "Red Chair",
      "metadata": {
        "type": "chair",
        "label": "Red Chair",
        "locked": false
      },
      "material": {
        "albedoColor": { "r": 1, "g": 0, "b": 0 }
      },
      "position": { "x": 2, "y": 0, "z": 1 },
      "rotation": { "x": 0, "y": 45, "z": 0 },
      "scaling": { "x": 1, "y": 1, "z": 1 },
      "parent_id": null,
      "visible": true
    }
  ]
}
```

### Input field notes

| Field | Notes |
|---|---|
| `transcript` | Plain string from whispercpp output |
| `user.position` | World space, y ≈ 1.7 = standing eye height |
| `user.look_direction` | Normalised vector |
| `user.point_target` | World-space hit point from BabylonJS raycast (`pick.pickedPoint`). Use to resolve "that", "this", "it". Parser finds the closest scene object to this point. |
| `scene[].id` | Server-assigned string — use exactly as-is in command output |
| `scene[].position` | World space — frontend must use `getAbsolutePosition()`, not `mesh.position` |
| `scene[].rotation` | Euler degrees — frontend converts from `absoluteRotationQuaternion` before sending |
| `scene` | Filtered — only objects where `metadata.type` is defined. Babylon internals (`BackgroundMesh`, `BackgroundHelper`, `__root__`) are excluded. |

---

## Output format (AI server → frontend)

A single JSON object. The frontend passes this directly to `executeEdit()`, `executeSpawn()`, or `executeDelete()` — no transformation needed.

### Example output for the input above

```json
{
  "command": "edit",
  "id": "server_abc123",
  "changes": {
    "position_relative": {
      "direction": "left",
      "units": 1
    }
  }
}
```

---

## What to build next

1. **Spin up Qwen locally via ollama** on Wilbur (the lab workstation with two NVIDIA A6000 GPUs)
2. **Write a minimal Python test script** that:
   - Constructs the request JSON with a hardcoded scene and transcript
   - Calls the Qwen model with the system prompt above
   - Prints and validates the JSON output
3. **Write 15–20 test cases by hand** — a mix of move (relative + absolute), delete, spawn, no-command, and ambiguous reference cases
4. **Score the baseline** — track: valid JSON output, correct `command` field, correct `id` resolution
5. That score becomes the benchmark to beat if we later fine-tune

---

## Open questions (non-blocking for now)

- Unit scale confirmation with Balsa: is 1 unit = 1 metre?
- When user says "spawn near the window" — should the parser estimate position from the scene graph, or always defer to the frontend for placement?
- Locked objects (`metadata.locked = true`) — should the parser skip them or output the command and let the server reject it?
- Room/session ID: the scene graph includes `metadata.roomId` per object — does the server need this in the top-level request body too?

---

## Project context

- **Intern:** Uroš Aron Čolović, graduation internship at Trans Realities Lab, High Tech Campus Eindhoven
- **Company supervisor:** Zak Lennard
- **Frontend developer:** Balsa (BabylonJS scene graph spec provided — used to define this interface)
- **AI mentors:** Leon van Bokhorst (Wednesdays), Coen Crombach (Thursdays)
- **Stack constraint:** fully local, open-source, no external API calls. EU-origin models preferred (Mistral) but non-EU open-source allowed with justification.
- **Hardware:** Wilbur workstation (2× NVIDIA A6000), accessible remotely from MacBook M4 Pro
- **Phase:** Sprint 2–3 of 7. ASR done (whispercpp selected). Now building parser baseline.
