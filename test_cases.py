# Hand-written test cases for the Holodeck parser baseline.
#
# Each case is a dict with:
#   "id"          – short identifier
#   "category"    – test category label
#   "transcript"  – voice command string
#   "user"        – user context (position, look_direction, point_target)
#   "scene"       – scene graph snapshot
#   "expected"    – the exact JSON object the parser should return
#
# Scoring in eval.py checks three things independently:
#   valid_json      – output parses as JSON
#   correct_command – "command" field matches expected
#   correct_id      – "id" field matches expected (where applicable)

DEFAULT_USER = {
    "id": "user_1",
    "position": {"x": 0, "y": 1.7, "z": 3},
    "look_direction": {"x": 0, "y": 0, "z": -1},
    "point_target": None,
}

CASES = [
    # ── 1. Relative move — cardinal direction + small magnitude ────────────────
    {
        "id": "rel_move_left_bit",
        "category": "relative_move",
        "transcript": "move the red chair a bit to the left",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_abc123",
                "name": "Red Chair",
                "metadata": {"type": "chair", "label": "Red Chair"},
                "material": {"albedoColor": {"r": 1, "g": 0, "b": 0}},
                "position": {"x": 2, "y": 0, "z": 1},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_abc123",
            "changes": {"position_relative": {"direction": "left", "units": 1}},
        },
    },
    # ── 2. Relative move — forward + medium magnitude ──────────────────────────
    {
        "id": "rel_move_forward_few",
        "category": "relative_move",
        "transcript": "push the table forward a few units",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_b77f2",
                "name": "Oak Table",
                "metadata": {"type": "table", "label": "Oak Table"},
                "position": {"x": 0, "y": 0, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_b77f2",
            "changes": {"position_relative": {"direction": "forward", "units": 3}},
        },
    },
    # ── 3. Relative move — up + large magnitude ────────────────────────────────
    {
        "id": "rel_move_up_lot",
        "category": "relative_move",
        "transcript": "raise the lamp a lot",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_e112c",
                "name": "Desk Lamp",
                "metadata": {"type": "lamp", "label": "Desk Lamp"},
                "position": {"x": 1, "y": 1, "z": 1},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_e112c",
            "changes": {"position_relative": {"direction": "up", "units": 10}},
        },
    },
    # ── 4. Relative move — right + slight magnitude ────────────────────────────
    {
        "id": "rel_move_right_slightly",
        "category": "relative_move",
        "transcript": "slide the sphere slightly to the right",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_c991a",
                "name": "Blue Sphere",
                "metadata": {"type": "sphere", "label": "Blue Sphere"},
                "material": {"albedoColor": {"r": 0, "g": 0, "b": 1}},
                "position": {"x": 3, "y": 1, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_c991a",
            "changes": {"position_relative": {"direction": "right", "units": 1}},
        },
    },
    # ── 5. Absolute move — explicit coordinates ────────────────────────────────
    {
        "id": "abs_move_coords",
        "category": "absolute_move",
        "transcript": "put the table at position 5, 0, minus 3",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_b77f2",
                "name": "Oak Table",
                "metadata": {"type": "table", "label": "Oak Table"},
                "position": {"x": 0, "y": 0, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_b77f2",
            "changes": {"position": {"x": 5, "y": 0, "z": -3}},
        },
    },
    # ── 6. Absolute move — fractional coordinates ──────────────────────────────
    {
        "id": "abs_move_fractional",
        "category": "absolute_move",
        "transcript": "move the chair to 1.5, 0, 2.5",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_abc123",
                "name": "Red Chair",
                "metadata": {"type": "chair", "label": "Red Chair"},
                "material": {"albedoColor": {"r": 1, "g": 0, "b": 0}},
                "position": {"x": 2, "y": 0, "z": 1},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_abc123",
            "changes": {"position": {"x": 1.5, "y": 0, "z": 2.5}},
        },
    },
    # ── 7. Delete — simple named object ───────────────────────────────────────
    {
        "id": "delete_simple",
        "category": "delete",
        "transcript": "delete the sphere",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_c991a",
                "name": "Blue Sphere",
                "metadata": {"type": "sphere", "label": "Blue Sphere"},
                "position": {"x": 3, "y": 1, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "delete",
            "id": "server_c991a",
            "deleteChildren": False,
        },
    },
    # ── 8. Delete — remove everything ─────────────────────────────────────────
    {
        "id": "delete_with_children",
        "category": "delete",
        "transcript": "delete the lamp and everything attached to it",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_e112c",
                "name": "Desk Lamp",
                "metadata": {"type": "lamp", "label": "Desk Lamp"},
                "position": {"x": 1, "y": 1, "z": 1},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "delete",
            "id": "server_e112c",
            "deleteChildren": True,
        },
    },
    # ── 9. Spawn — position inferred from nearby scene object ──────────────────
    {
        "id": "spawn_near_object",
        "category": "spawn",
        "transcript": "spawn a wooden chair near the window",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_d004b",
                "name": "Window Frame",
                "metadata": {"type": "plane", "label": "Window Frame"},
                "position": {"x": 0, "y": 1, "z": -5},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "spawn",
            "id": None,
            "asset_query": "wooden chair",
        },
    },
    # ── 10. Spawn — empty scene, no position context ───────────────────────────
    {
        "id": "spawn_empty_scene",
        "category": "spawn",
        "transcript": "add a small round table",
        "user": DEFAULT_USER,
        "scene": [],
        "expected": {
            "command": "spawn",
            "id": None,
            "asset_query": "small round table",
        },
    },
    # ── 11. Hide object ────────────────────────────────────────────────────────
    {
        "id": "hide_object",
        "category": "visibility",
        "transcript": "hide the lamp",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_e112c",
                "name": "Desk Lamp",
                "metadata": {"type": "lamp", "label": "Desk Lamp"},
                "position": {"x": 1, "y": 1, "z": 1},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_e112c",
            "changes": {"visible": False},
        },
    },
    # ── 12. Show object ────────────────────────────────────────────────────────
    {
        "id": "show_object",
        "category": "visibility",
        "transcript": "show the sphere again",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_c991a",
                "name": "Blue Sphere",
                "metadata": {"type": "sphere", "label": "Blue Sphere"},
                "position": {"x": 3, "y": 1, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": False,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_c991a",
            "changes": {"visible": True},
        },
    },
    # ── 13. Rotate object ──────────────────────────────────────────────────────
    {
        "id": "rotate_object",
        "category": "rotate",
        "transcript": "rotate the table 90 degrees",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_b77f2",
                "name": "Oak Table",
                "metadata": {"type": "table", "label": "Oak Table"},
                "position": {"x": 0, "y": 0, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_b77f2",
            "changes": {"rotation": {"x": 0, "y": 90, "z": 0}},
        },
    },
    # ── 14. Scale object ───────────────────────────────────────────────────────
    {
        "id": "scale_object",
        "category": "scale",
        "transcript": "make the sphere twice as big",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_c991a",
                "name": "Blue Sphere",
                "metadata": {"type": "sphere", "label": "Blue Sphere"},
                "position": {"x": 3, "y": 1, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_c991a",
            "changes": {"scaling": {"x": 2, "y": 2, "z": 2}},
        },
    },
    # ── 15. No command — question ──────────────────────────────────────────────
    {
        "id": "no_command_question",
        "category": "no_command",
        "transcript": "what do you think of this layout?",
        "user": DEFAULT_USER,
        "scene": [],
        "expected": {"command": "none"},
    },
    # ── 16. No command — filler speech ────────────────────────────────────────
    {
        "id": "no_command_filler",
        "category": "no_command",
        "transcript": "okay yeah um",
        "user": DEFAULT_USER,
        "scene": [],
        "expected": {"command": "none"},
    },
    # ── 17. Ambiguous reference — "that" resolved via point_target ─────────────
    # point_target is close to server_abc123 (chair at x=2, y=0, z=1)
    {
        "id": "point_target_resolution",
        "category": "ambiguous_reference",
        "transcript": "move that a bit to the right",
        "user": {
            **DEFAULT_USER,
            "point_target": {"x": 1.9, "y": 0.1, "z": 1.1},
        },
        "scene": [
            {
                "id": "server_abc123",
                "name": "Red Chair",
                "metadata": {"type": "chair", "label": "Red Chair"},
                "material": {"albedoColor": {"r": 1, "g": 0, "b": 0}},
                "position": {"x": 2, "y": 0, "z": 1},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            },
            {
                "id": "server_b77f2",
                "name": "Oak Table",
                "metadata": {"type": "table", "label": "Oak Table"},
                "position": {"x": -4, "y": 0, "z": -3},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            },
        ],
        "expected": {
            "command": "edit",
            "id": "server_abc123",
            "changes": {"position_relative": {"direction": "right", "units": 1}},
        },
    },
    # ── 18. Ambiguous reference — two chairs, colour disambiguation ────────────
    {
        "id": "ambiguous_two_chairs",
        "category": "ambiguous_reference",
        "transcript": "delete the blue chair",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_abc123",
                "name": "Red Chair",
                "metadata": {"type": "chair", "label": "Red Chair"},
                "material": {"albedoColor": {"r": 1, "g": 0, "b": 0}},
                "position": {"x": 2, "y": 0, "z": 1},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            },
            {
                "id": "server_f3391",
                "name": "Blue Chair",
                "metadata": {"type": "chair", "label": "Blue Chair"},
                "material": {"albedoColor": {"r": 0, "g": 0, "b": 1}},
                "position": {"x": -1, "y": 0, "z": 2},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            },
        ],
        "expected": {
            "command": "delete",
            "id": "server_f3391",
            "deleteChildren": False,
        },
    },
    # ── 19. Unresolvable object — target not in scene ──────────────────────────
    {
        "id": "unresolvable_object",
        "category": "unresolvable",
        "transcript": "delete the green sofa",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_abc123",
                "name": "Red Chair",
                "metadata": {"type": "chair", "label": "Red Chair"},
                "material": {"albedoColor": {"r": 1, "g": 0, "b": 0}},
                "position": {"x": 2, "y": 0, "z": 1},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "delete",
            "id": None,
        },
    },
    # ── 20. Relative move — back direction ────────────────────────────────────
    {
        "id": "rel_move_back",
        "category": "relative_move",
        "transcript": "push the table back a little",
        "user": DEFAULT_USER,
        "scene": [
            {
                "id": "server_b77f2",
                "name": "Oak Table",
                "metadata": {"type": "table", "label": "Oak Table"},
                "position": {"x": 0, "y": 0, "z": 0},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "scaling": {"x": 1, "y": 1, "z": 1},
                "visible": True,
            }
        ],
        "expected": {
            "command": "edit",
            "id": "server_b77f2",
            "changes": {"position_relative": {"direction": "back", "units": 1}},
        },
    },
]
