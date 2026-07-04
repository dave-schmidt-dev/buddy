"""The Textual view: a widget that paints the creature onto the pane.

This is the ONLY rendering module that imports Textual. It calls the pure
``render.compose_frame`` (INV-2) and maps each cell's "kind" to a color: ground
dim green, bubble soft cyan, and every sprite cell to the critter's body color or
one of its per-part accent colors (the kind code is the mask key). Keeping color
here (not in render.py) preserves the framework-free core (INV-4).
"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget

from buddy import render
from buddy.render import K_ALERT, K_BUBBLE, K_EMPTY, K_GROUND

# Non-sprite kind colors. Sprite cells resolve against the critter's palette.
GROUND_STYLE = "#4b5d3a"  # dim mossy green
BUBBLE_STYLE = "#88c0d0"  # soft cyan
ALERT_EXTREME_STYLE = "#bf616a"  # red for Extreme severity
ALERT_SEVERE_STYLE = "#d08770"  # amber for Severe severity


class StageWidget(Widget):
    """Renders the app's current creature, refreshed each animation tick."""

    def render(self) -> Text:
        app = self.app
        creature = getattr(app, "creature", None)
        cols, rows = self.size.width, self.size.height
        if creature is None or cols <= 0 or rows <= 0:
            return Text("")

        frame = render.compose_frame(creature, cols, rows)
        critter = creature.critter
        body, parts = critter.body, critter.parts
        text = Text()
        for r, (row, kinds) in enumerate(zip(frame.rows, frame.kinds, strict=True)):
            if r:
                text.append("\n")
            for ch, kind in zip(row, kinds, strict=True):
                if kind == K_EMPTY:
                    text.append(ch)
                elif kind == K_GROUND:
                    text.append(ch, style=GROUND_STYLE)
                elif kind == K_BUBBLE:
                    text.append(ch, style=BUBBLE_STYLE)
                elif kind == K_ALERT:
                    text.append(
                        ch,
                        style=ALERT_EXTREME_STYLE
                        if creature.alert_level == "Extreme"
                        else ALERT_SEVERE_STYLE,
                    )
                else:
                    # Sprite cell: an accent mask key (parts) or K_SPRITE -> body.
                    text.append(ch, style=parts.get(kind, body))
        return text
