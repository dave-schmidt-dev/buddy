"""Configuration dataclass and module-level constants for buddy."""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Module-level constants — hand-picked defaults, adjustable as the project grows.
# ---------------------------------------------------------------------------

FPS = 8  # Base animation frames per second
WALK_STEP = 1  # Columns moved per walk frame

IDLE_TICKS_RANGE = (12, 30)  # Min/max ticks to stay idle before transitioning
WALK_TICKS_RANGE = (20, 60)  # Min/max ticks to walk before stopping
NAP_TICKS = 60  # Duration of a nap in ticks
BLINK_TICKS = 2  # Duration of a blink in ticks (brief)
BUBBLE_TICKS = 40  # How long a speech bubble lingers

BLINK_PROB = 0.05  # Per-tick probability of a blink
TALK_PROB = 0.02  # Per-tick probability of a talk bubble appearing
NAP_PROB = 0.01  # Per-tick probability of falling asleep

FRAME_ADVANCE_TICKS = 2  # Ticks between sprite frame swaps (leg cadence)

# The sprite takes one WALK_STEP column each time its legs advance a frame, so
# footfalls land with the stride instead of gliding independently.
TURN_PAUSE_FRAMES = 5  # Leg-frames the critter pauses to "turn" after hitting a wall

# Idle "breathing": a slow 1-row lift so a standing critter isn't a frozen statue.
# One breath every BREATH_PERIOD ticks; the lift is held for the second half.
BREATH_PERIOD = 20  # Ticks per breath cycle (~2.5s at FPS=8)
BREATH_HOLD = 6  # Ticks of the cycle spent lifted by one row

MIN_STAGE_COLS = 24  # Supported minimum stage width; below this show "too small" notice
MIN_STAGE_ROWS = 8  # Supported minimum stage height; below this show "too small" notice

MAX_BUBBLE_WIDTH = 22  # Maximum character width of a speech bubble

SPEED_MIN = 0.0  # Exclusive lower bound for --speed
SPEED_MAX = 10.0  # Inclusive upper bound for --speed

LOG_PATH = "/tmp/buddy.log"  # Rotating log file destination


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------


@dataclass
class BuddyConfig:
    """Runtime configuration for a buddy session.

    All fields have sensible defaults; override via CLI or programmatic
    construction.
    """

    animal: str = "random"  # Which critter to render, or "random"
    speed: float = 1.0  # Animation speed multiplier (SPEED_MIN < x <= SPEED_MAX)
    seed: int | None = None  # Optional RNG seed for reproducible playback
    animate: bool = True  # Whether to run animations (False = static snapshot)
    debug: bool = False  # Enable DEBUG-level logging
