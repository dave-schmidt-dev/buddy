"""Critter art registry — the dumb ASCII frame data for buddy.

Part of the framework-free core (INV-4): imports no Textual, holds no runtime
state. Each :class:`Critter` is plain data — a ``body`` hex color, a ``parts`` map
of accent-key -> hex color, and animation ``states``. Every frame carries two
parallel grids of identical size: ``art`` (the glyphs) and ``mask`` (a per-cell
part key naming which color that glyph takes; a space means the body color). All
frames of a critter are normalized to one bounding box so the sprite never jitters
as it animates (INV-1); the mask is normalized to that same box.

Every critter faces the viewer with the same build: ears, a face (eyes/nose), a
body, and a feet row. Only idle/blink/nap are authored; the walk pose is *derived*
by keeping the head + torso fixed and shuffling the feet row side to side, so the
face — and its eyes — stay put and the walk reads without a cramped side silhouette.

Mask keys: a=accent  e=eye  n=nose  t=teeth  k=beak  g=tongue  l=tail  f=foot
z=zzz. A critter only colors the keys it lists in ``parts``; any other key (and
the body) falls back to the body color, so partial masks are fine.
"""

from __future__ import annotations

from dataclasses import dataclass

# State name constants — shared with creature.py so the two modules agree.
WALK = "walk"
IDLE = "idle"
BLINK = "blink"
NAP = "nap"
STATES = (WALK, IDLE, BLINK, NAP)

# Global accent colors applied to any critter that does not override the key in its
# own ``parts``. Eyes get a light color (the sprite is line art on a dark terminal,
# so a dark eye would vanish); the nap "z" gets a faint cyan so sleep reads.
PART_DEFAULTS: dict[str, str] = {
    "e": "#e5e9f0",  # bright eye — must be light to read on a dark background
    "z": "#6d8a94",  # faint cyan zzz
}

# The four walk phases as a horizontal shift of the feet row: neutral, forward,
# neutral, back. Paired with the sprite's vertical bob it reads as a shuffle-walk.
_FOOT_SHIFTS = (0, 1, 0, -1)


@dataclass(frozen=True)
class Frame:
    """One animation frame: glyph rows plus a same-sized part-key mask."""

    art: tuple[str, ...]
    mask: tuple[str, ...]


@dataclass(frozen=True)
class Critter:
    """A single critter's art and palette.

    Attributes:
        name: Registry key (e.g. ``"cat"``).
        body: Base body color as a hex string (e.g. ``"#e0873c"``).
        parts: Map of mask key -> hex color for accented cells.
        states: Map of state name -> tuple of frames.
        walk_left: Walk frames when travelling left. Critters face the viewer, so
            this is the same tuple as the rightward walk (kept for the render seam).
        width: Uniform frame width (columns).
        height: Uniform frame height (rows).
    """

    name: str
    body: str
    parts: dict[str, str]
    states: dict[str, tuple[Frame, ...]]
    walk_left: tuple[Frame, ...]
    width: int
    height: int

    def frame(self, state: str, index: int, *, facing_left: bool = False) -> Frame:
        """Return the frame for *state* at *index* (walk is direction-agnostic)."""
        frames = self.walk_left if (facing_left and state == WALK) else self.states[state]
        return frames[index % len(frames)]


def _F(art: list[str], mask: list[str]) -> tuple[list[str], list[str]]:
    """Raw (art, mask) pair used in the roster; normalized by :func:`_make`."""
    return (art, mask)


def _shift(row: str, d: int) -> str:
    """Shift a row *d* columns (positive = right), clipped to its original width."""
    w = len(row)
    if d > 0:
        return (" " * d + row)[:w]
    if d < 0:
        return (row[-d:] + " " * (-d))[:w]
    return row


def _make(entry: dict) -> Critter:
    """Build a normalized :class:`Critter`.

    Walk is derived from the idle: keep the head + torso, shuffle the feet row so the
    face stays put and only the feet move.
    """
    idle_art, idle_mask = entry["idle"]
    body_art, body_mask = idle_art[:-1], idle_mask[:-1]
    foot_art, foot_mask = idle_art[-1], idle_mask[-1]
    walk_raw = [
        (body_art + [_shift(foot_art, d)], body_mask + [_shift(foot_mask, d)]) for d in _FOOT_SHIFTS
    ]

    frames_raw = {
        WALK: walk_raw,
        IDLE: [entry["idle"]],
        BLINK: [entry["blink"]],
        NAP: [entry["nap"]],
    }
    all_art = [a for pairs in frames_raw.values() for (a, _m) in pairs]
    width = max(len(row) for art in all_art for row in art)
    height = max(len(art) for art in all_art)

    def norm(art: list[str], mask: list[str]) -> Frame:
        def pad(lines: list[str]) -> tuple[str, ...]:
            body = [ln.ljust(width) for ln in lines]
            top = [" " * width] * (height - len(lines))
            return tuple(top + body)

        mask = list(mask) + [""] * (len(art) - len(mask))
        return Frame(art=pad(art), mask=pad(mask))

    states = {
        state: tuple(norm(art, mask) for (art, mask) in pairs)
        for state, pairs in frames_raw.items()
    }
    return Critter(
        name=entry["name"],
        body=entry["body"],
        parts={**PART_DEFAULTS, **entry["parts"]},
        states=states,
        walk_left=states[WALK],
        width=width,
        height=height,
    )


# ---------------------------------------------------------------------------
# The roster. Only idle/blink/nap are authored (front-facing); walk is derived.
# ---------------------------------------------------------------------------

_ROSTER: list[dict] = [
    {
        "name": "cat",
        "body": "#e0873c",
        "parts": {"a": "#f0ead8"},
        # Ginger body, cream ears/whiskers, pink nose.
        "idle": _F(
            art=[
                "  /\\_/\\  ",
                "=( o.o )=",
                " (  ^  ) ",
                " (_____) ",
                "  u   u  ",
            ],
            mask=[
                "         ",
                "a  ene  a",
                "    n    ",
                "         ",
                "  f   f  ",
            ],
        ),
        "blink": _F(
            art=[
                "  /\\_/\\  ",
                "=( -.- )=",
                " (  ^  ) ",
                " (_____) ",
                "  u   u  ",
            ],
            mask=[
                "         ",
                "a  ene  a",
                "    n    ",
                "         ",
                "  f   f  ",
            ],
        ),
        "nap": _F(
            art=[
                "       z ",
                " ,-----. ",
                " ( -.- ) ",
                " (_____) ",
                "         ",
            ],
            mask=[
                "       z ",
                "         ",
                "   ene   ",
                "         ",
                "         ",
            ],
        ),
    },
    {
        "name": "rabbit",
        "body": "#d9d3cf",
        "parts": {"a": "#f0e8ea", "t": "#ffffff"},
        # Soft beige, white tail + teeth, tall ears.
        "idle": _F(
            art=[
                "  || ||  ",
                " (|| ||) ",
                "=( o.o )=",
                " (_ w _) ",
                "  u   u  ",
            ],
            mask=[
                "         ",
                "         ",
                "a  ene  a",
                "    t    ",
                "  f   f  ",
            ],
        ),
        "blink": _F(
            art=[
                "  || ||  ",
                " (|| ||) ",
                "=( -.- )=",
                " (_ w _) ",
                "  u   u  ",
            ],
            mask=[
                "         ",
                "         ",
                "a  ene  a",
                "    t    ",
                "  f   f  ",
            ],
        ),
        "nap": _F(
            art=[
                "       z ",
                " (\\___/) ",
                " ( -.- ) ",
                " (_____) ",
                "         ",
            ],
            mask=[
                "       z ",
                "         ",
                "   ene   ",
                "         ",
                "         ",
            ],
        ),
    },
    {
        "name": "duck",
        "body": "#ecd884",
        "parts": {"k": "#e8912e", "f": "#e8912e"},
        # Cream body, orange beak + feet, wide flat bill.
        "idle": _F(
            art=[
                " ( o o ) ",
                " <=====> ",
                "( _____ )",
                " \\_____/ ",
                "  w   w  ",
            ],
            mask=[
                "   e e   ",
                " kkkkkkk ",
                "         ",
                "         ",
                "  f   f  ",
            ],
        ),
        "blink": _F(
            art=[
                " ( - - ) ",
                " <=====> ",
                "( _____ )",
                " \\_____/ ",
                "  w   w  ",
            ],
            mask=[
                "   e e   ",
                " kkkkkkk ",
                "         ",
                "         ",
                "  f   f  ",
            ],
        ),
        "nap": _F(
            art=[
                "       z ",
                " ( -.- ) ",
                "( _____ )",
                " \\_____/ ",
                "         ",
            ],
            mask=[
                "       z ",
                "   ene   ",
                "         ",
                "         ",
                "         ",
            ],
        ),
    },
    {
        "name": "possum",
        "body": "#b9bfca",
        "parts": {"a": "#e79ab0", "n": "#e79ab0", "l": "#d8b8a0"},
        # Cool grey, pink round ears + nose, tan tail.
        "idle": _F(
            art=[
                " ()   () ",
                " ( o.o ) ",
                " ( \\v/ ) ",
                " (_____) ",
                "  u   u  ",
            ],
            mask=[
                " aa   aa ",
                "   ene   ",
                "    n    ",
                "         ",
                "  f   f  ",
            ],
        ),
        "blink": _F(
            art=[
                " ()   () ",
                " ( -.- ) ",
                " ( \\v/ ) ",
                " (_____) ",
                "  u   u  ",
            ],
            mask=[
                " aa   aa ",
                "   ene   ",
                "    n    ",
                "         ",
                "  f   f  ",
            ],
        ),
        "nap": _F(
            art=[
                "       z ",
                " ()   () ",
                " ( -.- ) ",
                " (_____) ",
                "         ",
            ],
            mask=[
                "       z ",
                " aa   aa ",
                "   ene   ",
                "         ",
                "         ",
            ],
        ),
    },
]


CRITTERS: dict[str, Critter] = {e["name"]: _make(e) for e in _ROSTER}


def names() -> list[str]:
    """Return the sorted list of available critter names."""
    return sorted(CRITTERS)


def get(name: str) -> Critter:
    """Return the :class:`Critter` for *name*.

    Raises:
        KeyError: If *name* is not a registered critter.
    """
    try:
        return CRITTERS[name]
    except KeyError:
        raise KeyError(f"unknown critter {name!r}; choices: {', '.join(names())}") from None
