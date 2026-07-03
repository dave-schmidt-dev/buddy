# Invariants — buddy

> System contract. The harvest tool reads `area:` globs to map HISTORY bug entries
> to invariants. Per-project convention (commit prefix, invariant refs) is declared
> in this project's CLAUDE.md/README, not globally.

### INV-1 — Every animation frame of a given critter, normalized, is a rectangle of identical width and height across all that critter's states — and each frame's color mask is the same rectangle as its art
area: ["src/buddy/critters.py"]
gate_test: tests/test_critters.py
threshold: 3
rationale: Frames that differ in width/height within a critter make the sprite jitter as it animates and cause index errors when the renderer blits a ragged frame onto the fixed-size grid. A uniform per-critter bounding box is what keeps motion smooth and blitting safe. The per-cell color mask must match its art cell-for-cell, or the view would color the wrong glyphs (or index out of range) — so the mask is normalized to the same box, and mirrored walk frames preserve it.

### INV-2 — The stage renderer never writes outside the grid or indexes out of range, at any pane size — degrading gracefully below the supported minimum (24x8) and never crashing down to a 1x1 floor
area: ["src/buddy/render.py", "src/buddy/stage.py"]
gate_test: tests/test_stage.py
threshold: 3
rationale: A roaming creature and its speech bubble routinely reach the stage edges; a resized-small pane shrinks the grid. Unclipped drawing produces IndexError crashes exactly when the companion is most visible. All blitting must clip to bounds. The pure clipping logic lives in render.py (framework-free, so the invariant test imports no Textual); stage.py is the thin Textual widget wrapper. Supported minimum is 24x8 (below which a "too small" notice is shown); the renderer must not raise at any size down to 1x1.

### INV-3 — All randomness (state transitions, dialogue selection, spawn position) flows through an injected random.Random instance; no module-level random.* calls; the same seed yields an identical run
area: ["src/buddy/creature.py", "src/buddy/dialogue.py"]
gate_test: tests/test_creature.py
threshold: 3
rationale: Module-level randomness makes the state machine non-reproducible, which makes behavior unprovable and snapshots flaky. Seed injection is the precondition for deterministic tests and reproducible bug reports.

### INV-4 — The framework-free set (creature.py, critters.py, dialogue.py, render.py) imports no Textual; the model/view split holds
area: ["src/buddy/creature.py", "src/buddy/critters.py", "src/buddy/dialogue.py", "src/buddy/render.py"]
gate_test: tests/test_core_is_framework_free.py
threshold: 3
rationale: If the state machine, art data, or pure renderer pull in Textual, that logic can only be exercised through a terminal, which is slow and flaky to test. Keeping this set framework-free is what allows ~90% of the app — including the INV-2 clipping logic in render.py — to be unit-tested headless.

### INV-5 — The default run performs no subprocess or network I/O; the default reactor is NullReactor; any git/file-watch/hook reactor is opt-in behind an explicit flag
area: ["src/buddy/**"]
gate_test: tests/test_default_is_passive.py
threshold: 3
rationale: buddy sits in a terminal beside real work. A cute companion silently shelling out (git) or opening sockets is a trust and security violation. Reactivity must be a deliberate, flagged opt-in, never the ambient default.
