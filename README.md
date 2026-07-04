# buddy

An ambient ASCII-art coding companion — a colored line-art critter that struts around a side terminal pane while you work in Claude Code or Codex.

**Status:** v1 + ambient feeds — 4 critters, 194 tests green.

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
| `src/buddy/` | Package source: `critters` (art), `creature` (state machine), `render`/`stage` (view), `app`, `cli`, `dialogue`, `events`, `feeds`, `devsheet`. |
| `tests/` | Unit + snapshot tests (one gate test per invariant). |

## Planning artifacts

- Charter: `INVARIANTS.md` (the INV-1..INV-5 system contracts) + `ledger.yaml`.
- History and open work: `HISTORY.md` and `TASKS.md`.

## Workflows

### Run it

The `./buddy` launcher is the simplest way — it works from the project root and
keeps working even when macOS re-hides `.venv` (see the dev note below):

```bash
./buddy                      # random critter
./buddy --animal duck        # pick one
./buddy --list               # list critters
./buddy --speed 1.5          # faster strut (0 < speed <= 10)
./buddy --seed 42            # reproducible run
./buddy --debug              # DEBUG logging to /tmp/buddy-<pid>.log
```

Want it available everywhere? Add one alias to your shell (`~/.zshrc`):

```bash
alias buddy='/Users/dave/Documents/Projects/buddy/buddy'
```

Then just `buddy` from any directory. (The installed `.venv/bin/buddy` console
script also works, but it's the one that breaks under the hidden-`.venv` quirk;
prefer the launcher.)

Keys while running: `q` quit · `space` next critter · `t` talk.

Critters: cat, duck, possum, rabbit.
Each has a muted body color plus per-part accents (eyes, nose, beak, tongue, tail,
feet) driven by a color mask. A critter idles, blinks, and naps face-on; the walk
keeps the face forward with feet shuffling side-to-side and body bobbing — popping
the occasional speech-bubble tip.

### Ambient feeds

The `./buddy` launcher turns on all three feeds by default (it passes
`--feeds hn,weather,nws`), reading your location from a local `.env`. The library
default stays passive: `python -m buddy` (and `BuddyConfig()`) run with no feeds and
no network. The deliberate opt-in lives in the launcher, so INV-5 still holds — the
code default reactor is `NullReactor` unless a `--feeds` flag is explicitly passed.

```bash
./buddy                                # all feeds on (hn + weather + nws), location from .env
./buddy --feeds hn                     # override: headlines only
./buddy --feeds ""                     # override: passive, no feeds
./buddy --feeds weather,nws --lat 38.9 --lon -77.0   # explicit coordinates
python -m buddy                        # passive (no launcher default)
```

The three feeds:
- `hn` — Hacker News top-story tech headlines (~15 min).
- `weather` — NWS current conditions plus a varied rotation: temperature, wind,
  humidity, a comfort note (e.g. "muggy out"), the day's high, and a near-term
  precip heads-up (~10 min).
- `nws` — NWS active weather alerts: warnings, watches, advisories (~3 min).
  Severe/Extreme alerts preempt the bubble, wake the critter from a nap, and hold.
  They also render distinctly — a `(! ... !)` frame colored red (Extreme) or amber
  (Severe) — so a warning never looks like an ordinary headline or quip.

Headlines and weather fold into the normal talk rotation.

**Location** (for `weather`/`nws`): set it once in a local `.env` (copy `.env.example`):

```bash
BUDDY_ZIP=20169            # or BUDDY_LAT / BUDDY_LON
```

or pass `--lat`/`--lon` or `--zip` on the command line (CLI args win over `.env`).
If no location can be resolved, the weather/nws feeds are simply skipped (with a
logged warning) and the companion still launches — `hn` keeps working. All sources
are keyless — no API keys, no secrets. `.env` is gitignored.

**PRIVACY:** enabling `weather`/`nws` sends your approximate coordinates to
api.weather.gov; `--zip` (or `BUDDY_ZIP`) sends the ZIP to api.zippopotam.us.

### Beside your work (side pane)

```bash
tmux split-window -h "$PWD/buddy"   # buddy in a vertical split
```

Or just open a second terminal and run `buddy` (with the alias above) there while
you work in Claude Code or Codex in the first.

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
- Secrets in BWS. Never committed. (buddy has no secrets; network is opt-in behind `--feeds` per INV-5.)
- Update `HISTORY.md` alongside every meaningful change. Bug entries cite the files touched (`- files: path/a.py, path/b.ts`).
- Tests verify real behavior — no smoke-only "did it run" checks. Behavioral core is unit-tested headless; the TUI is snapshot-tested via `pytest-textual-snapshot`.
- Every change must uphold every invariant in `INVARIANTS.md`.
