"""Developer contact sheet: dump every critter x state x frame to the terminal,
tinted in each critter's color, so the art can be eyeballed and iterated.

Run it:  python -m buddy.devsheet
This is a DEV tool (it may import Rich); it is not part of the framework-free core.
"""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

from buddy import critters
from buddy.critters import STATES, WALK, Critter, Frame


def _frame_block(c: Critter, frame: Frame, indent: int) -> Text:
    """Render one frame as an indented, per-part-colored Text block."""
    block = Text()
    for r, (row, mrow) in enumerate(zip(frame.art, frame.mask, strict=True)):
        if r:
            block.append("\n" + " " * indent)
        for x, ch in enumerate(row):
            key = mrow[x] if x < len(mrow) else " "
            block.append(ch, style=c.parts.get(key, c.body) if key != " " else c.body)
    return block


def build_sheet() -> Text:
    """Assemble the full contact sheet as a single Rich Text object."""
    out = Text()
    for name in critters.names():
        c = critters.get(name)
        out.append(f"\n{name}  ", style="bold")
        out.append(f"{c.body}  {c.width}x{c.height}\n", style=c.body)
        for state in STATES:
            for i, frame in enumerate(c.states[state]):
                out.append(f"  {state}#{i}".ljust(12), style="dim")
                out.append(_frame_block(c, frame, 12))
                out.append("\n")
            # Show the left-facing walk right after the right-facing one so both
            # directions can be eyeballed (hand-authored for cat/capybara, else mirrored).
            if state == WALK:
                for i, frame in enumerate(c.walk_left):
                    out.append(f"  walkL#{i}".ljust(12), style="dim")
                    out.append(_frame_block(c, frame, 12))
                    out.append("\n")
    return out


def main() -> int:
    """Print the contact sheet and return an exit code."""
    console = Console()
    console.print(build_sheet())
    console.print(f"\n[dim]{len(critters.names())} critters: {', '.join(critters.names())}[/dim]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
