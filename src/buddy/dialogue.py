"""Dialogue data and helpers for buddy's speech bubbles.

Pure stdlib module — no I/O, no framework imports (INV-4).
All randomness flows through an injected ``random.Random`` instance (INV-3).
"""

from __future__ import annotations

import random  # imported for type hint only; never called at module level

from buddy.config import MAX_BUBBLE_WIDTH

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

CATEGORIES: tuple[str, ...] = ("tips", "encouragement", "quips")

DIALOGUE: dict[str, list[str]] = {
    "tips": [
        "commit early",
        "name it clearly",
        "read the error first",
        "test the edge case",
        "small functions win",
        "delete unused code",
        "type your returns",
        "log before you guess",
        "lint before you push",
        "write the test first",
        "grep first, ask later",
    ],
    "encouragement": [
        "you got this",
        "nice fix!",
        "keep going",
        "clean code!",
        "almost there",
        "proud of you!",
        "that's the way",
        "you're on a roll",
        "solid progress!",
        "looking good in here",
    ],
    "quips": [
        "*stretches*",
        "any snacks?",
        "nap soon...",
        "ooh, a shiny bug",
        "*wiggles ears*",
        "your code smells nice",
        "*tail wag*",
        "is it nap time yet?",
        "boop.",
        "*blinks slowly*",
        "unbothered, thriving",
        "brb, dissociating",
        "no thoughts, cozy",
        "touch grass? nah",
        "5 more minutes",
        "chronically online",
    ],
}

# Per-species flavor — cute, funny lines relevant to each animal. Keyed by critter
# name (must match buddy.critters names). A talking critter mostly says one of these
# (see SPECIES_MIX) and otherwise draws from the general pools above.
SPECIES: dict[str, list[str]] = {
    "cat": [
        "nap now, code later",
        "chasing the cursor",
        "pet me, then commit",
        "9 lives, 0 bugs",
        "found a sun spot",
        "knocked it off. oops",
        "if it fits, i sits",
        "cursor = prey",
        "judging your code",
        "box-driven design",
        "refactoring my nap",
        "plotting, as usual",
        "rent free up here",
        "i has commits?",
        "the audacity of bugs",
        "loaf mode: on",
        "sun spot > standup",
        "3am zoomies",
        "the disrespect",
        "i own this repo now",
        "sun's out, naps out",
    ],
    "duck": [
        "rubber duck says hi",
        "quack the bug away",
        "just ducky!",
        "waddle we do now?",
        "bread-driven dev",
        "float, don't sink",
        "quack-end dev",
        "ducks in a row",
        "bug off, human",
        "pond-side standup",
        "splashing tests",
        "quack overflow",
        "what the duck?!",
        "you quack me up",
        "pond vibes only",
        "keep calm, quack on",
        "quack is the new black",
        "here for the bread",
        "duck, duck, deploy",
        "just here to vibe",
        "quack to work",
    ],
    "rabbit": [
        "hop to it!",
        "carrot break?",
        "quick like a bunny",
        "tasks multiply fast",
        "ears up, focus up",
        "i'll bounce back",
        "burrow into the docs",
        "twitchy about typos",
        "24 carrots gold",
        "hoppy commits",
        "fast feet, clean diff",
        "what's up, doc?",
        "down the rabbit hole",
        "no thoughts, just hop",
        "carrot loading...",
        "some bunny loves u",
        "binky! happy hop",
        "zoomies engaged",
        "i carrot about it",
        "hoppin' mad at bugs",
        "carrot > deadline",
        "back to the burrow",
    ],
    "possum": [
        "playing dead til 5",
        "night shift dev",
        "hang in there!",
        "not a trash panda",
        "*hisses politely*",
        "nocturnal by design",
        "play dead, ship later",
        "tail-recursive nap",
        "hiss at conflicts",
        "found snacks in trash",
        "just a lil guy",
        "hey, i'm down here",
        "no thoughts, only hiss",
        "5am trash goblin",
        "anxiety, but cute",
        "i am the night shift",
        "found a snacc",
        "vibes: feral",
        "screaming internally",
        "livin in ur walls",
    ],
}

# When a critter talks, the chance it says a species line vs. a general one.
SPECIES_MIX = 0.6

# Guard: catch any line that exceeds the bubble width at import time. Use an
# explicit raise (not assert) so the check survives `python -O`.
_too_wide = [
    line
    for pool in (*DIALOGUE.values(), *SPECIES.values())
    for line in pool
    if len(line) > MAX_BUBBLE_WIDTH
]
if _too_wide:
    raise ValueError(f"dialogue lines exceed MAX_BUBBLE_WIDTH ({MAX_BUBBLE_WIDTH}): {_too_wide}")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def pick(rng: random.Random, category: str) -> str:
    """Return a random line from the given dialogue category.

    Args:
        rng: A ``random.Random`` instance supplied by the caller. Using an
            injected RNG keeps the module side-effect-free (INV-3).
        category: One of the strings in ``CATEGORIES``.

    Returns:
        A randomly selected line from ``DIALOGUE[category]``.

    Raises:
        ValueError: If ``category`` is not in ``CATEGORIES``.
    """
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category {category!r}. Choose one of: {', '.join(CATEGORIES)}")
    return rng.choice(DIALOGUE[category])


def speak(rng: random.Random, name: str) -> str:
    """Return a line for critter *name* to say.

    Mostly species flavor (``SPECIES_MIX`` of the time, when the critter has its own
    lines), otherwise a line from one of the general pools. A critter without species
    lines always falls back to the general pools.

    Args:
        rng: Injected ``random.Random`` (INV-3).
        name: The critter's registry name (e.g. ``"cat"``).
    """
    lines = SPECIES.get(name)
    if lines and rng.random() < SPECIES_MIX:
        return rng.choice(lines)
    return pick(rng, rng.choice(CATEGORIES))


def all_lines() -> list[str]:
    """Return every dialogue line — general pools plus every species pool.

    Useful for validation — e.g. checking that no line exceeds the bubble width and
    that anything a critter says comes from a known pool.

    Returns:
        A flat list of strings (general lines first, then species lines).
    """
    general = [line for lines in DIALOGUE.values() for line in lines]
    species = [line for lines in SPECIES.values() for line in lines]
    return general + species


def format_feed_line(text: str, width: int = MAX_BUBBLE_WIDTH, ellipsis: str = "...") -> str:
    """Collapse and truncate *text* so it fits within *width* characters.

    Collapses internal whitespace runs to a single space and strips leading/trailing
    whitespace before measuring. If the collapsed text already fits, it is returned
    unchanged. Otherwise it is truncated and the *ellipsis* suffix is appended.

    Postcondition: ``len(result) <= width`` for every input.

    Args:
        text: The raw string to format (e.g. a news headline or feed entry).
        width: Maximum number of characters in the returned string. Defaults to
            ``MAX_BUBBLE_WIDTH``.
        ellipsis: Suffix appended when truncation is needed. Defaults to ``"..."``.

    Returns:
        A string of at most *width* characters.
    """
    collapsed = " ".join(text.split())
    if len(collapsed) <= width:
        return collapsed
    if width >= len(ellipsis):
        return collapsed[: width - len(ellipsis)] + ellipsis
    return collapsed[:width]
