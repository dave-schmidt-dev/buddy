# Tasks

> Live queue for **current, pending, and future** work — never history. Completed work belongs in `HISTORY.md`.

Status key: `pending | in progress | done | blocked`

## Rules

- Never trample another session's in-flight or pending work.
- Update status as work progresses.
- Only mark `done` after verification (tests pass, behavior confirmed).
- `done` is **transient**: after verification, port the row's substance into `HISTORY.md` and delete the row from `TASKS.md` in the same change.
- If a completed task is worth remembering, that's a `HISTORY.md` entry — not a `TASKS.md` preservation.
- Smell test: if `done` rows outnumber open rows, the file has drifted into a log. Clean it up.
- Keep tasks small and actionable — one unit of work each.

## Open

v1 is built and green with the design-pass art (see HISTORY.md 2026-07-03). Remaining work:

### Task (deferred): Real reactivity via the event seam
- **Status:** pending
- **Description:** Implement `GitReactor` / `FileWatchReactor` (currently inert stubs)
  behind an explicit opt-in flag, so the critter reacts to git status / file saves /
  Claude Code hook events. Must stay opt-in — INV-5 keeps the default run passive.
  (The ambient `FeedReactor` is implemented — see HISTORY.md 2026-07-04. This task
  is specifically about the git/file-watch/hook-event reactors.)
- **Blocked by:** none (future enhancement)
- **Done when:**
  - A flagged run reacts to real activity; default run remains passive (INV-5 test still green).

### Task (deferred): Per-PID log path
- **Status:** pending
- **Description:** `/tmp/buddy.log` is shared across instances; give concurrent
  instances distinct log files if multi-instance use becomes common.
