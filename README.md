# buddy

An ambient ASCII-art coding companion — a colored line-art critter that struts around a side terminal pane while you work in Claude Code or Codex.

**Status:** v1 implemented — ambient companion runs, 9 critters with per-part color, full test gate green.

## Priorities (in order)

1. **Delightful and unobtrusive** — charming to glance at, never in the way of real work.
2. **Portable** — renders on any 256-color terminal; runs beside both Claude Code and Codex.
3. **Testable and deterministic** — seeded behavioral core, snapshot-verified TUI, no "manual only" gaps.
4. **Extensible** — new critters and the reactivity seam plug in without a rewrite.

## Layout

| Path | Purpose |
|---|---|
| `README.md` | This file. |
| `HISTORY.md` | Meaningful changes, bugs, remediation, regression notes. |
| `TASKS.md` | Per-project task tracking. |
| `INVARIANTS.md` | Closed-loop charter — MUST-hold system contracts (INV-1..INV-5). |
| `ledger.yaml` | Machine state for the closed-loop harvest tool. |
| `LICENSE` | MIT. |
| `src/buddy/` | Package source: `critters` (art), `creature` (state machine), `render`/`stage` (view), `app`, `cli`, `dialogue`, `events`, `devsheet`. |
| `tests/` | Unit + snapshot tests (one gate test per invariant). |

## Planning artifacts

- Charter: `INVARIANTS.md` (the INV-1..INV-5 system contracts) + `ledger.yaml`.
- History and open work: `HISTORY.md` and `TASKS.md`.

## Workflows

### Run it

```bash
# from the project root, using the project venv
.venv/bin/buddy                      # random critter
.venv/bin/buddy --animal capybara    # pick one
.venv/bin/buddy --list               # list critters
.venv/bin/buddy --speed 1.5          # faster strut (0 < speed <= 10)
.venv/bin/buddy --seed 42            # reproducible run
.venv/bin/buddy --debug              # DEBUG logging to /tmp/buddy.log
```

Keys while running: `q` quit · `space` next critter · `t` talk.

Critters: cat, duck, capybara, rabbit, dog, possum, sloth, hedgehog, armadillo.
Each has a muted body color plus per-part accents (eyes, nose, beak, tongue, tail,
feet) driven by a color mask. A critter idles, blinks, and naps face-on; the walk
keeps the face forward with feet shuffling side-to-side and body bobbing — popping
the occasional speech-bubble tip.

### Beside your work (side pane)

```bash
tmux split-window -h '.venv/bin/buddy'   # buddy in a vertical split
```

Or just open a second terminal and run `buddy` there while you work in Claude Code
or Codex in the first.

### Iterate on the art

```bash
python -m buddy.devsheet   # colored contact sheet of every critter x state x frame
```

### Validation gate

All checks are **local** — there is no CI. The gate (`make check` = ruff lint +
`ruff format --check` + the full pytest suite) runs **automatically on every commit**
via a tracked git hook (`hooks/pre-commit`). You don't run anything by hand; a commit
that fails the gate is rejected.

`make install` activates the hook (it runs `git config core.hooksPath hooks`); on a
fresh clone, `make hooks` alone does the same one-time wiring. git never
auto-activates hooks from a clone, so that single step is the only setup.

To run the gate manually anyway (or the pieces):

```bash
make check                        # the whole gate, on demand
.venv/bin/python -m pytest        # unit + snapshot tests (regen: --snapshot-update)
.venv/bin/ruff check src tests    # lint
.venv/bin/ruff format --check src tests   # formatting
```

### Dev note (macOS + Python 3.14 venv quirk)

Something in this environment recursively re-sets the `UF_HIDDEN` flag on `.venv`,
and Python 3.14's `site.py` skips `.pth` files whose **own file** carries that flag
(the directory flag doesn't matter; `uchg` doesn't help — the owner's `chflags -R
hidden` stacks on top). That silently kills the editable install, so `.venv/bin/buddy`
fails with `ModuleNotFoundError: No module named 'buddy'`.

Durable fix (already applied): a **symlink** `…/site-packages/buddy -> src/buddy`.
A symlinked package is resolved by the normal import finder, which — unlike `.pth`
processing — does **not** skip hidden entries, so it imports even with the whole
`.venv` hidden, and stays live (points at `src/`). Recreate it any time with:

```
make fix-venv     # (re)links src/buddy into site-packages, clears UF_HIDDEN
make link         # just (re)create the symlink
```

`make install` sets it up automatically. The test suite is independent either way:
`pyproject.toml` sets pytest `pythonpath = ["src"]`, and `make run`/`make sheet` use
`PYTHONPATH=src`, so those always import live source regardless of the flag.

## Conventions

- All files self-contained under this directory.
- Secrets in BWS. Never committed. (buddy has no secrets today; passive by default per INV-5.)
- Update `HISTORY.md` alongside every meaningful change. Bug entries cite the files touched (`- files: path/a.py, path/b.ts`).
- Tests verify real behavior — no smoke-only "did it run" checks. Behavioral core is unit-tested headless; the TUI is snapshot-tested via `pytest-textual-snapshot`.
- Every change must uphold every invariant in `INVARIANTS.md`.
