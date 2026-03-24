# Parser Observations & Known Limitations

Running notes on model behaviour, schema gaps, and things to investigate.
Add entries as you test — date and model version each time.

---

## Format

```
### [YYYY-MM-DD] Short description
**Model:** <model name>
**Trigger:** <transcript that caused it>
**Observed:** <what the model actually output>
**Expected:** <what it should have output>
**Notes:** <analysis, hypothesis, or follow-up action>
```

---

## Entries

### [2026-03-24] Colour change returns `{"command": "none"}`
**Model:** qwen3.5:9b  
**Trigger:** `"make the red chair blue"`  
**Observed:** `{"command": "none"}`  
**Expected:** Some form of material/colour edit command  
**Notes:** Colour changes are not in the v2 schema at all — the model has no valid command to emit, so it correctly falls back to `none`. If recolouring is a real user need, a `material` field needs to be added to the edit schema (e.g. `"changes": {"material": {"albedoColor": {"r": 0, "g": 0, "b": 1}}}`). Discuss with Balsa whether the frontend `executeEdit()` already supports material changes.

---

### [2026-03-24] Compound move command silently drops one axis
**Model:** qwen3.5:9b  
**Trigger:** `"move the red chair a bit to the left and up a lot"`  
**Observed:** `{"command": "edit", "id": "server_abc123", "changes": {"position_relative": {"direction": "up", "units": 10}}}`  
**Expected:** Both the left and up moves represented  
**Notes:** The schema only allows a single `position_relative` per command. The model picks one and drops the other — silently, no error. This is a known schema limitation, not a model failure. Options: (a) accept it and document it as out of scope for v1, (b) add a `commands` array to the output schema to support multi-step sequences. Not blocking for baseline but worth flagging for Zak/Balsa.

---

### [2026-03-24] `spawn_near_object` fails on 0.8b
**Model:** qwen3.5:0.8b  
**Trigger:** `"spawn a wooden chair near the window"`  
**Observed:** FAIL on both `command` and `id` fields  
**Notes:** The 0.8b model appears to mishandle spawn commands when a scene object is present — likely conflating the window object's ID with the spawn target. The 9b handles this correctly. Spawn near a reference object may be above the capability threshold of the 0.8b model. Re-test with 9b and 14b to confirm it's model-size-dependent.

---

### [2026-03-24] 0.8b hangs indefinitely on complex prompts
**Model:** qwen3.5:0.8b  
**Trigger:** `point_target_resolution` case — two objects in scene, non-null `point_target`, transcript "move that a bit to the right". Also reproduced on the very first case in a second run.  
**Observed:** Process hung indefinitely (15+ minutes), never returned a response  
**Expected:** Sub-20s response  
**Notes:** This is NOT the formal thinking mode (which is off by default for 0.8b and was never enabled). The model card warns the 0.8b has unstable generation dynamics under complex prompts — it enters repetitive token-level loops and cannot find a stopping point. This is a raw generation failure, not a reasoning feature. The 0.8b appears below the reliability threshold for this task. Mitigation applied: `num_predict: 512` added to all ollama calls, but this does not fully prevent the hang in practice with ollama's streaming behaviour. Recommendation: use 9b or larger for evals.

---

### [2026-03-24] 4b returns empty content on 8/20 cases due to num_predict cap
**Model:** qwen3.5:4b  
**Score:** Valid JSON 12/20, Command 12/20, ID 11/18  
**Trigger:** `num_predict: 512` cap introduced to prevent 0.8b infinite loops  
**Observed:** 7 cases returned empty `content`, 1 case (`ambiguous_two_chairs`) returned `{"command": "delete", "id` — cut off mid-token. Failures appeared on structurally simple cases (e.g. `rel_move_left_bit`) while equivalent cases passed, suggesting variable-length internal reasoning rather than capability failure.  
**Notes:** The 4b model uses an internal thinking phase before outputting JSON. With ollama, thinking tokens go into `response["message"]["thinking"]`, not `content`. When `num_predict: 512` is hit during the thinking phase, generation stops and `content` is empty. Fix: raised `num_predict` to 2048. A thinking trace for this task is typically 200–800 tokens; JSON output is ~80 tokens. 2048 gives safe headroom without restoring the 0.8b infinite-loop risk.

---

### [2026-03-24] Inconsistent latency on 0.8b
**Model:** qwen3.5:0.8b  
**Notes:** Some cases resolve in ~1 second (`delete_simple`: 1080ms, `hide_object`: 1313ms) while others spike to 12–19 seconds (`rel_move_left_bit`: 14402ms, `abs_move_fractional`: 17467ms, `spawn_near_object`: 19673ms). The slow cases tend to involve larger scene graphs or more complex reasoning. Not a correctness issue but relevant for real-time voice interaction latency targets.
