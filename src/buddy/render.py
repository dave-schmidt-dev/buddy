"""Pure grid composition — the framework-free renderer (INV-2, INV-4).

``compose_frame`` paints the creature, ground line, and optional speech bubble onto
a fixed ``rows x cols`` character grid, returning that grid plus a parallel "kind"
grid tagging each cell as sprite / ground / bubble / empty. The view (stage.py) maps
kinds to colors; this module imports no Textual and applies no color itself, so the
clipping invariant can be tested headless.

Every write is clipped to the grid, so the renderer never raises no matter where the
creature is or how small the stage gets (down to 1x1). Below the supported minimum
(config.MIN_STAGE_COLS x MIN_STAGE_ROWS) it shows a "too small" notice instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from buddy import config

if TYPE_CHECKING:  # pragma: no cover - typing only
    from buddy.creature import Creature

# Kind codes for the parallel style grid. Non-sprite cells use these fixed
# uppercase/space codes; sprite cells carry either K_SPRITE (body color) or the
# critter's lowercase mask key (accent color), which the view resolves per critter.
K_EMPTY = " "
K_SPRITE = "S"
K_GROUND = "G"
K_BUBBLE = "B"
K_ALERT = "A"

GROUND_CHAR = "~"


@dataclass(frozen=True)
class Rendered:
    """A composed frame: character rows and a parallel kind grid (same dims)."""

    rows: list[str]
    kinds: list[str]

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def width(self) -> int:
        return len(self.rows[0]) if self.rows else 0


def _put(grid, kinds, x, y, ch, kind, cols, rows, *, skip_space=True) -> None:
    """Write one cell, clipped to the grid. Spaces are transparent by default."""
    if not (0 <= y < rows and 0 <= x < cols):
        return
    if skip_space and ch == " ":
        return
    grid[y][x] = ch
    kinds[y][x] = kind


def _finish(grid, kinds) -> Rendered:
    return Rendered(
        rows=["".join(row) for row in grid],
        kinds=["".join(row) for row in kinds],
    )


def _blit_notice(grid, kinds, cols, rows) -> None:
    msgs = ["stage too small", f"min {config.MIN_STAGE_COLS}x{config.MIN_STAGE_ROWS}"]
    top = rows // 2 - len(msgs) // 2
    for j, msg in enumerate(msgs):
        y = top + j
        x = cols // 2 - len(msg) // 2
        for i, ch in enumerate(msg):
            _put(grid, kinds, x + i, y, ch, K_BUBBLE, cols, rows, skip_space=False)


def _blit_bubble(grid, kinds, creature: Creature, cols, rows) -> None:
    is_alert = creature.alert_level is not None
    kind = K_ALERT if is_alert else K_BUBBLE
    bubble = f"(! {creature.message} !)" if is_alert else f"( {creature.message} )"
    w = len(bubble)
    center = creature.x + creature.critter.width // 2
    bx = center - w // 2
    # Clamp so the bubble starts on-screen. When it is wider than the stage this
    # pins it to the left edge and the right side clips (still never crashes).
    bx = max(0, min(bx, cols - w))
    by = max(0, creature.sprite_y() - 2)
    for i, ch in enumerate(bubble):
        _put(grid, kinds, bx + i, by, ch, kind, cols, rows, skip_space=False)
    _put(grid, kinds, center, by + 1, "\\", kind, cols, rows, skip_space=False)


def compose_frame(creature: Creature, cols: int, rows: int) -> Rendered:
    """Compose the current creature state onto a ``rows x cols`` grid.

    Args:
        creature: The model to draw (provides position, frame, message).
        cols: Grid width. Values < 1 are treated as empty.
        rows: Grid height.

    Returns:
        A :class:`Rendered` whose ``rows`` and ``kinds`` are each exactly ``rows``
        strings of exactly ``cols`` characters. Never raises.
    """
    cols = max(0, cols)
    rows = max(0, rows)
    grid = [[" "] * cols for _ in range(rows)]
    kinds = [[K_EMPTY] * cols for _ in range(rows)]

    if cols < config.MIN_STAGE_COLS or rows < config.MIN_STAGE_ROWS:
        _blit_notice(grid, kinds, cols, rows)
        return _finish(grid, kinds)

    # Ground line along the bottom row.
    ground_y = rows - 1
    for x in range(cols):
        _put(grid, kinds, x, ground_y, GROUND_CHAR, K_GROUND, cols, rows, skip_space=False)

    # Sprite (spaces transparent so it sits over the ground cleanly). Each cell's
    # kind is its mask key (accent) or K_SPRITE (body) when the mask cell is blank.
    frame = creature.current_frame()
    sx, sy = creature.x, creature.sprite_y()
    for dy, (line, mline) in enumerate(zip(frame.art, frame.mask, strict=True)):
        for dx, ch in enumerate(line):
            key = mline[dx] if dx < len(mline) else " "
            kind = K_SPRITE if key == " " else key
            _put(grid, kinds, sx + dx, sy + dy, ch, kind, cols, rows)

    if creature.message:
        _blit_bubble(grid, kinds, creature, cols, rows)

    return _finish(grid, kinds)
