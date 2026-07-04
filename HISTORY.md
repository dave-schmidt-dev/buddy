# History

Meaningful changes, bugs, remediation, and regression notes for the `buddy` project. Newest first.

---

## 2026-07-03 — `./buddy` launcher script

Added a one-line start script at the repo root: `./buddy [args]`. It runs the app
via `PYTHONPATH=src .venv/bin/python -m buddy`, so it imports the source tree
directly and keeps working even when macOS re-hides `.venv` and the installed
`.venv/bin/buddy` console-script shim stops resolving (the same quirk the
site-packages symlink works around). Verified it launches with `.venv` fully hidden.
README documents it plus a `~/.zshrc` alias (`alias buddy='…/buddy'`) for global use.

- [change] add `./buddy` launcher; document launcher + shell alias | files: buddy
  (new), README.md
- Not linted/tested by the gate (shell script; `make check` scopes ruff/pytest to
  `src`/`tests`), but exercised manually: `--list` works, and launches under a hidden
  `.venv`.

---

## 2026-07-03 — Drop CI; the gate runs automatically via a local git hook

Removed the GitHub Actions workflow (`.github/workflows/ci.yml`) added during the
initial ship — quality gating is local now, not hosted. But "local" must not mean
"run it by hand": the gate runs **automatically on every commit** through a tracked
git hook (`hooks/pre-commit`, activated by `core.hooksPath=hooks`). The hook runs
`make check` = ruff lint + `ruff format --check` + the full pytest suite (unit +
snapshots); a commit that fails the gate is rejected. Formatting was folded into the
gate (new `make fmt`) so nothing the old workflow caught is lost.

Iteration on the shape (all same day): first the workflow was replaced by a hand-run
`make check`, and the earlier `.pre-commit-config.yaml` (which needed `pre-commit
install` + the `pre-commit` package) was dropped. That still required typing the gate
by hand, which wasn't the goal — so the final form is a dependency-free native git
hook that self-runs. `make install` / `make hooks` does the one-time `core.hooksPath`
wiring (git never auto-activates hooks from a clone). ruff stays pinned at 0.15.20 in
the venv and the pyproject dev dep, so lint/format are version-consistent.

- Rationale: solo, small project — a hosted CI run per push was unrequested overhead,
  but the checks still need to run without manual effort. A local pre-commit hook is
  the fit. The Node-20→24 action-deprecation warning CI emitted is moot now.

- [change] remove CI workflow; add self-running `hooks/pre-commit` that runs the full
  `make check` gate on every commit; wire `make install`/`make hooks` to activate it |
  files: .github/workflows/ci.yml (deleted), .pre-commit-config.yaml (deleted),
  hooks/pre-commit (new), Makefile, README.md
- Gate: `make check` green — ruff clean, 24 files formatted, 156 tests pass. Verified
  the hook fires by committing through it (see the commit that carried this entry).

---

## 2026-07-03 — Species dialogue: each critter says its own thing

Added per-critter speech: `dialogue.SPECIES` maps each critter name to a pool of
cute/funny, species-relevant lines (duck: "rubber duck says hi"; dog: "who's a good
dev?"; capybara: "unbothered coder"; sloth: "one commit... someday"; possum:
"playing dead til 5"; etc.). New `dialogue.speak(rng, name)` returns a species line
`SPECIES_MIX` (0.6) of the time and a general tip/encouragement/quip otherwise; a
critter without a species pool falls back to the general pools. `creature`'s ambient
talk and the `t` keypress both route through `speak`, so bubbles are now flavored by
who's on screen.

- All species lines respect `MAX_BUBBLE_WIDTH` (the import-time guard now covers them
  too); `all_lines()` includes them so the width/validity gates apply.
- dialogue.py stays framework-free and standalone (SPECIES is keyed by plain name
  strings; the roster-coverage check lives in the test, not the module).

- [change] per-species speech-bubble lines + `speak()` selector | files: src/buddy/dialogue.py, src/buddy/creature.py
- Tests: 149 (+5): species pools cover the roster, speak stays within known pools,
  mixes species+general, is seed-deterministic, and falls back for unknown critters.
- files: src/buddy/dialogue.py, src/buddy/creature.py, tests/test_dialogue.py

---

## 2026-07-03 — Front-facing dog; drop the side-profile special case

The dog had been "just a head" — its idle was a front-on face with no body or feet,
which is why it alone needed a side-profile walk. Redrew the dog as a normal
front-facing critter (floppy brown ears, eyes, a snout with a pink tongue, body,
feet) at the shared 9x5 box, so it walks with the same feet-shuffle as everyone
else. That let me delete the entire side-profile path: `_GAITS`, `_mirror_row`,
`_MIRROR`, and the `walk_body`/`gait` branch in `_make`. Now every critter is
authored as idle/blink/nap only and the walk is derived — no exceptions.

- [change] redrew dog as a front-facing critter with a body + feet | files: src/buddy/critters.py
- [cleanup] removed the dog-only side-profile/gait machinery | files: src/buddy/critters.py
- Tests: 144 (dropped the dog-side-profile test; renamed the walk-box / animates
  tests to match). Snapshots unchanged.
- files: src/buddy/critters.py, tests/test_critters.py

---

## 2026-07-03 — Walk pivot: front-facing (keep the face), feet shuffle

Live review: the sideways cat read as a blob with "eyes in the middle of the body."
The root problem is structural — a legible side profile with a distinct head doesn't
fit in a 9-column sprite. Pivoted instead of fighting it: the walk now keeps the
critter facing the viewer, reusing the idle head + torso (so the eyes stay in the
face) and only animating the feet — the bottom row shuffles side to side (neutral /
forward / neutral / back) under a bobbing body.

- Walk is now *derived* from the idle for the 8 feet-having critters: no per-critter
  walk art, no left/right mirror (front-facing is symmetric). The gait/`walk_body`/
  `walk_body_left` machinery and the side-profile redraws are gone for them.
- The **dog** is the one exception — its idle is a front-on face with no feet row, so
  it keeps an explicit side-profile `walk_body` + `dogwalk` gait (its eye already
  sits in the head). `_make` branches on the presence of `walk_body`.

- [bug] sideways sprite unreadable — eyes floating in the body | files: src/buddy/critters.py
- [change] front-facing feet-shuffle walk derived from idle (dog keeps side profile) | files: src/buddy/critters.py | inv: INV-1
- Tests: 145 (front-walk keeps-face + dog-side-profile tests replace the explicit-left
  test; synthetic-critter test moved to the front-walk path). Snapshots unchanged
  (idle art/colors untouched).
- files: src/buddy/critters.py, tests/test_critters.py

---

## 2026-07-03 — Fixups: legible eyes + redrawn cat side profile

Two issues from live review on a dark terminal:
- **Eyes were invisible.** The eye default was `#2e3440` (near-black) — fine as a
  pupil on a light fill, but the sprite is line art on a black background, so dark
  eyes vanished. Switched the eye default to a light `#e5e9f0` so eyes read on dark.
- **The side-profile cat was a mess** (tail + ears + back crammed into 9 cols).
  Redrew the cat `walk_body` around the iconic `/\_/\` ears with a clean oval body,
  single eye, and snout — and dropped its hand-authored left body since the new
  body auto-mirrors cleanly.

- [bug] eye default too dark to see on a dark terminal | files: src/buddy/critters.py
- [change] redrew cat side profile; cat left walk now auto-mirrors | files: src/buddy/critters.py
- Tests: 144 (updated the explicit-left-body test for capybara-only); both snapshots
  regenerated for the lighter eye color.
- files: src/buddy/critters.py, tests/test_critters.py, tests/__snapshots__/

---

## 2026-07-03 — Polish pass: animated gait, live idle, cleaner side profiles

Reworked motion (engine) and the walk art (data) in one round so the critter reads
as alive rather than shuffling in place.

Engine (creature.py, config.py):
- **Footfall-synced stepping.** The sprite advances one column per leg-frame (not
  per tick), so steps land with the stride instead of gliding. `FRAME_ADVANCE_TICKS`
  3 -> 2 for a snappier cadence.
- **Turn-around beat.** Hitting a wall now flips direction and holds for
  `TURN_PAUSE_TICKS` frames — a little pause-and-turn instead of an instant bounce.
- **Idle breathing.** A slow 1-row lift (`BREATH_PERIOD`/`BREATH_HOLD`) while
  standing or napping, driven by a monotonic `anim_clock`, so idle isn't a frozen
  statue. Clock 0 yields no lift, keeping pinned snapshots stable.

Art (critters.py) — gait model:
- The walk pose is now **composed**: a fixed `walk_body` (head+torso) plus a named
  `gait` — a 4-phase leg-row cycle shared by build (`quad`, `bird`, `hop`,
  `dogwalk`). Every critter gets an animated 4-frame stride from a little data;
  legs cycle while the body stays put and the whole sprite bobs.
- Redrew the three weakest side profiles (possum, rabbit, sloth) and normalized
  hedgehog's legs via the shared quad gait.
- Removed the now-unused frame-level `_mirror` (dead code); left-facing walk mirrors
  the body + gait per row.

- [change] footfall-synced walk, turn-around pause, idle breathing | files: src/buddy/creature.py, src/buddy/config.py
- [change] gait-composed 4-frame walk + redrawn possum/rabbit/sloth profiles | files: src/buddy/critters.py | inv: INV-1
- Tests: 140 -> 144 (turn-pause, breathing on/off, gait animates legs + body stays,
  explicit-left-body roster check; updated the wall-bounce and synthetic-critter
  tests for the new model). Snapshots unchanged (idle art/colors untouched).
- files: src/buddy/creature.py, src/buddy/config.py, src/buddy/critters.py, tests/test_creature.py, tests/test_critters.py, tests/test_app_snapshot.py

---

## 2026-07-03 — Fix `.venv/bin/buddy` for good (hidden-.pth) + devsheet both directions

The console script kept failing with `ModuleNotFoundError: No module named 'buddy'`.
Root-caused it properly this time: this machine recursively re-applies macOS
`UF_HIDDEN` to `.venv`, and Python 3.14's `site.py` skips a `.pth` file when **that
file** is hidden (proven: dir-hidden + pth-visible imports fine; dir-visible +
pth-hidden fails). `chflags -R nohidden` isn't durable (the flag returns) and `uchg`
doesn't help (the owner's `chflags -R hidden` stacks on top). A `sitecustomize.py`
shim was a dead end too — homebrew's Python ships its own `sitecustomize` on the
stdlib path that shadows any in site-packages.

Fix: a **symlink** `…/site-packages/buddy -> src/buddy`. Symlinked packages are
resolved by the normal import finder, which does NOT skip hidden entries (verified:
a fully-hidden `textual` still imports), so `buddy` imports even with the entire
`.venv` hidden — and it stays live because it points at `src/`. Wired into the
Makefile (`make link`, `make install`, and `make fix-venv` recreate it); README dev
note rewritten with the real mechanism.

Also: the devsheet now prints the left-facing walk (`walkL#0/#1`) right after the
right-facing one, so both directions (hand-authored for cat/capybara, mirrored for
the rest) can be eyeballed while iterating.

- [bug] `.venv/bin/buddy` ModuleNotFoundError — editable `.pth` skipped by 3.14
  site.py when re-hidden; fixed with a live src symlink in site-packages (import
  finder ignores UF_HIDDEN) | files: Makefile, README.md, .venv/lib/.../site-packages/buddy (symlink)
- [change] devsheet shows both walk directions | files: src/buddy/devsheet.py
- files: Makefile, README.md, src/buddy/devsheet.py

---

## 2026-07-03 — Art polish: shared eye/zzz colors + hand-authored left walks

Three iteration tweaks on the design-pass art:

- **Global part defaults.** Added `PART_DEFAULTS` (eye `#2e3440` dark pupil, zzz
  `#6d8a94` faint cyan) merged into every critter's palette in `_make`, with a
  critter's own `parts` winning on any shared key. Eyes now read on every body and
  naps look sleepy without per-critter boilerplate. The mask already marked `e`/`z`
  cells, so this is a pure palette change — no art edits.
- **Hand-authored left walks for cat + capybara.** `_make` now uses explicit
  `w1L`/`w2L` frames when a roster entry supplies them, else falls back to the
  machine mirror. Cat and capybara got crisper left-facing frames (head/eye leads,
  tail trails); the other seven still mirror mechanically.

- [change] shared eye/zzz accent defaults + optional per-critter hand-authored
  left-walk frames | files: src/buddy/critters.py | inv: INV-1
- Tests: +3 (defaults present, merge-order override, cat/capybara override the
  mirror) -> 140. Both SVG snapshots regenerated (eye color changed).
- files: src/buddy/critters.py, tests/test_critters.py, tests/__snapshots__/

---

## 2026-07-03 — Design-pass art: 9 critters, per-part color, directional walk

Replaced the first-pass placeholder frames with the art from the Claude-design
brainstorm and expanded the data model to carry real color. The roster is now 9
(adds hedgehog + armadillo), resolving the open 7-vs-9 question with actual art.

Data model (`critters.py`):
- A frame is now a `Frame(art, mask)`: the glyph grid plus a same-sized "color
  mask" whose cells name a part (a=accent, e=eye, n=nose, t=teeth, k=beak,
  g=tongue, l=tail, f=foot, z=zzz); a blank mask cell means the body color.
- `Critter` gains `body` (base hex) + `parts` (mask-key -> hex). A critter only
  colors the keys it lists; any other key falls back to body, so partial masks are
  fine (e.g. most eyes are just body-colored glyphs).
- Two view sets: front-facing `idle`/`blink`/`nap`, and right-facing `walk`.
  Left-facing walk is generated by `_mirror` (reverse each row + swap paired glyphs
  `()<>[]{}/\\`); the mask is reversed in lockstep so it stays cell-aligned.
- The whole roster was extracted programmatically from the design bundle (gzip'd,
  double-escaped JS-in-JSON) and emitted via `repr()` so backslashes and the
  significant trailing spaces are byte-exact — no hand-transcription.

Plumbing:
- `render.compose_frame` now writes each sprite cell's mask key into the kind grid
  (or `K_SPRITE` for body cells); still framework-free (INV-4), still clips (INV-2).
- `stage.py` resolves each sprite cell via `parts.get(kind, body)` — body and any
  unlisted key collapse to the body color. `creature.current_frame` passes travel
  direction so walk mirrors with `dx`.
- `devsheet` now renders the contact sheet with real per-part color.

INV-1 extended: the color mask must be the same rectangle as its art, and mirrored
walk frames must preserve the box. New gate tests cover mask alignment, mirror
dimensions, mask-key legality, and the locked 9-critter roster.

- [change] art data model reshaped from `list[str]` frames to `Frame(art, mask)`
  with per-part color; consumers updated | files: src/buddy/critters.py, src/buddy/creature.py, src/buddy/render.py, src/buddy/stage.py, src/buddy/devsheet.py | inv: INV-1
- Tests: 110 -> 137 (parametrized tests now span 9 critters; added mirror/mask/
  roster gates). Both SVG snapshots regenerated for the new art (deterministic).
- files: src/buddy/critters.py, src/buddy/creature.py, src/buddy/render.py, src/buddy/stage.py, src/buddy/devsheet.py, tests/test_critters.py, tests/test_stage.py, tests/__snapshots__/, INVARIANTS.md, README.md, TASKS.md

---

## 2026-07-03 — Checkpoint: review + test-hardening pass

Ran the update workflow (independent reviewer + tester + Codex second opinion) on the
v1 build. No HIGH issues and no invariant violations; all 5 invariants independently
confirmed solid. Fixed 2 real bugs (Codex), 2 test-reliability bugs (reviewer), and 5
polish items; added coverage. Suite 98 -> 110 tests, ruff clean.

- [bug] setup_logging idempotent early-return left the existing handler at its old
  level, so setup_logging(False) then (True) silently dropped DEBUG records (--debug
  ineffective if called twice) | files: src/buddy/logging_config.py
- [bug] --animal was not enforced by argparse; an unknown value reached
  BuddyApp and raised a raw ValueError from list.index instead of a clean parser
  error | files: src/buddy/cli.py, src/buddy/app.py
- [bug] nap/blink wakeup tests ticked N+1, letting the woken creature re-roll state;
  they passed only on seed 42 by luck (confirmed failing on seeds 9/16). Now tick
  exactly N (the rng-free wakeup tick) — seed-independent across 200 seeds |
  files: tests/test_creature.py | inv: INV-3
- [bug] INV-4 subprocess import-check used a relative PYTHONPATH and wiped os.environ,
  risking silent miscoverage when pytest runs from another cwd | files: tests/test_stage.py | inv: INV-4
- [cleanup] dialogue width guard changed from assert to explicit raise (survives
  `python -O`); app _tick assert -> None-guard; render bubble left-edge now always
  clamped (over-wide bubble pins to col 0, reachable at the 24-col minimum); fixed a
  misleading creature comment; removed a banned phrase from a critters docstring |
  files: src/buddy/dialogue.py, src/buddy/app.py, src/buddy/render.py, src/buddy/creature.py, src/buddy/critters.py
- Coverage added: tests/test_logging_config.py (level/idempotency incl. the debug
  re-enable regression), tests/test_app.py (cycle/talk/resize/animate-gating via
  run_test), tests/test_cli.py (--animal enforcement + main app-launch).
- files: src/buddy/logging_config.py, src/buddy/cli.py, src/buddy/app.py, src/buddy/render.py, src/buddy/dialogue.py, src/buddy/creature.py, src/buddy/critters.py, tests/test_creature.py, tests/test_stage.py, tests/test_default_is_passive.py, tests/test_logging_config.py, tests/test_app.py, tests/test_cli.py

---

## 2026-07-03 — v1 implemented: ambient ASCII companion

Built buddy v1 via subagent-driven execution of the impulse-tier plan. A Textual
side-pane app renders a colored line-art critter that struts (horizontal move +
bob), idles, blinks, naps, and pops speech-bubble tips. 7 critters (cat, duck,
capybara, rabbit, dog, possum, sloth), each a muted flat color.

Architecture — sprite/model/view split:
- `critters.py` — dumb ASCII frame data + per-critter color; `normalize()` pins one
  bounding box per critter (INV-1).
- `creature.py` — pure, seeded state machine (walk/idle/blink/nap + talk overlay),
  deterministic under an injected `random.Random` (INV-3).
- `render.py` — pure `compose_frame` returning a char grid + parallel "kind" grid;
  clips all drawing to bounds, never raises down to 1x1 (INV-2). Framework-free.
- `stage.py` — Textual widget; maps kinds -> color (sprite = critter color, ground
  dim green, bubble soft cyan). Only module importing Textual for rendering.
- `app.py` — interval loop gated on `config.animate` (deterministic snapshots);
  NullReactor default (INV-5); keys q/space/t.
- `events.py` — reactor seam; NullReactor default, Git/FileWatch stubs lazy-import
  subprocess/os inside methods so the default path stays passive (INV-5).
- `cli.py` — argparse; `--speed` validated to (0, 10]; app imported lazily.
- `dialogue.py`, `devsheet.py`, `logging_config.py` (rotating /tmp/buddy.log).

Color feature added mid-build at user request: pure renderer emits a kind grid; the
view applies color, so INV-1/INV-2/INV-4 stay testable on plain text and SVG
snapshots regression-test the palette for free.

Tests: 98 pass (unit + 2 SVG snapshots), ruff clean. All 5 invariants have live gate
tests; `ledger.yaml` INV-1..INV-5 = covered.

Notable environment issue + fix: on this macOS + Python 3.14 machine, `.venv` keeps
getting the `UF_HIDDEN` flag re-applied, and 3.14's `site.py` skips hidden editable
`.pth` files, so the `buddy` console script intermittently can't import `buddy`.
Mitigated by setting pytest `pythonpath = ["src"]` (gate is immune) and documenting
`chflags -R nohidden .venv` / `PYTHONPATH=src` for manual runs.

- files: src/buddy/{__init__,__main__,config,cli,logging_config,critters,creature,dialogue,render,stage,events,app,devsheet}.py, tests/{test_cli,test_critters,test_dialogue,test_creature,test_stage,test_core_is_framework_free,test_default_is_passive,test_app_snapshot}.py, pyproject.toml, ledger.yaml, README.md

---

## 2026-07-03 — Project folder scaffolded + charter bootstrapped

Initial scaffold of `~/Documents/Projects/buddy/`:

- `README.md` — purpose, priorities, layout, conventions.
- `HISTORY.md` — this file.
- `TASKS.md` — task tracking.
- `LICENSE` — MIT.
- `.gitignore` — venv, secrets, OS artifacts.

Closed-loop charter bootstrapped during first `:plan` run (impulse tier): `INVARIANTS.md` +
`ledger.yaml` with INV-1..INV-5 (frame-box integrity, renderer clips to bounds, seeded
determinism, framework-free core, passive by default). Environment verified: Python 3.14.6,
Textual 8.2.8, pytest 8.4.2, pytest-textual-snapshot all install and run headless in `.venv`.

- files: README.md, HISTORY.md, TASKS.md, LICENSE, .gitignore, INVARIANTS.md, ledger.yaml
