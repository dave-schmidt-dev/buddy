"""INV-1 gate: every critter's frames (art AND color mask) share one bounding box
and stay monospace-safe, so the sprite never jitters and the renderer can blit it
onto a fixed grid without surprises.
"""

from __future__ import annotations

import unicodedata

import pytest

from buddy import critters
from buddy.critters import STATES


def _all_frames(c):
    return [f for frames in c.states.values() for f in frames]


@pytest.mark.parametrize("name", critters.names())
def test_all_frames_share_one_bounding_box(name):
    """INV-1: within a critter, every frame's art and mask are width x height."""
    c = critters.get(name)
    for state, frames in c.states.items():
        for i, frame in enumerate(frames):
            for label, grid in (("art", frame.art), ("mask", frame.mask)):
                assert len(grid) == c.height, (
                    f"{name}/{state}#{i} {label}: height {len(grid)} != {c.height}"
                )
                for row_idx, row in enumerate(grid):
                    assert len(row) == c.width, (
                        f"{name}/{state}#{i} {label} row {row_idx}: width {len(row)} != {c.width}"
                    )


@pytest.mark.parametrize("name", critters.names())
def test_walk_left_matches_the_bounding_box(name):
    """Left-facing walk frames share the same box (critters face the viewer, so the
    left tuple is the right tuple — this guards that invariant too)."""
    c = critters.get(name)
    assert len(c.walk_left) == len(c.states["walk"])
    for frame in c.walk_left:
        assert len(frame.art) == c.height
        assert all(len(row) == c.width for row in frame.art)
        assert len(frame.mask) == c.height
        assert all(len(row) == c.width for row in frame.mask)


@pytest.mark.parametrize("name", critters.names())
def test_frames_have_no_tabs_or_control_chars(name):
    """Control chars / tabs would corrupt cursor positioning in the terminal."""
    c = critters.get(name)
    for frame in _all_frames(c):
        for row in frame.art:
            for ch in row:
                assert ch == " " or ch.isprintable(), f"{name}: non-printable char {ch!r}"
                assert ch != "\t", f"{name}: tab character present"


@pytest.mark.parametrize("name", critters.names())
def test_frames_are_single_width(name):
    """Every glyph must occupy exactly one monospace cell (no emoji/CJK/combining),
    or the fixed-width bounding box would not match on-screen columns."""
    c = critters.get(name)
    for frame in _all_frames(c):
        for row in frame.art:
            for ch in row:
                assert unicodedata.east_asian_width(ch) not in ("W", "F"), (
                    f"{name}: double-width char {ch!r}"
                )
                assert unicodedata.combining(ch) == 0, f"{name}: combining char {ch!r}"


@pytest.mark.parametrize("name", critters.names())
def test_mask_keys_are_colorable(name):
    """Every non-blank mask key is a single lowercase letter (a color slot). Keys a
    critter doesn't list in ``parts`` are legal — they fall back to the body color."""
    c = critters.get(name)
    for frame in _all_frames(c):
        for row in frame.mask:
            for ch in row:
                assert ch == " " or (ch.islower() and ch.isalpha()), f"{name}: bad mask key {ch!r}"


@pytest.mark.parametrize("name", critters.names())
def test_every_critter_defines_all_states(name):
    """The renderer and state machine assume all four states exist for any critter."""
    c = critters.get(name)
    for state in STATES:
        assert state in c.states and c.states[state], f"{name}: missing state {state}"


def test_walk_has_at_least_two_frames():
    """Walk needs >=2 frames to read as motion."""
    for name in critters.names():
        assert len(critters.get(name).states["walk"]) >= 2, f"{name}: walk needs >=2 frames"


def test_get_unknown_critter_raises():
    with pytest.raises(KeyError):
        critters.get("dragon")


def _is_hex(color) -> bool:
    return isinstance(color, str) and color.startswith("#") and len(color) == 7


def test_colors_are_hex_strings():
    """Every body and part color is a plain #rrggbb hex string (INV-4: no Textual)."""
    for name in critters.names():
        c = critters.get(name)
        assert _is_hex(c.body), f"{name}: bad body color {c.body!r}"
        for key, color in c.parts.items():
            assert _is_hex(color), f"{name}: bad part color {key}={color!r}"


def test_global_eye_and_zzz_defaults_present():
    """Every critter inherits the shared dark pupil + faint-cyan zzz so eyes read
    and naps look sleepy without per-critter boilerplate."""
    for name in critters.names():
        parts = critters.get(name).parts
        assert parts.get("e") == critters.PART_DEFAULTS["e"], f"{name}: missing eye default"
        assert parts.get("z") == critters.PART_DEFAULTS["z"], f"{name}: missing zzz default"


def test_per_critter_parts_override_global_defaults():
    """Merge order: a critter's own parts win over the shared defaults on a shared key."""
    c = critters._make(
        {
            "name": "x",
            "body": "#000000",
            "parts": {"e": "#ffffff"},  # overrides the global eye default
            "idle": (["ab", "cd"], ["", ""]),  # front-walk path (body row + feet row)
            "blink": (["ab", "cd"], ["", ""]),
            "nap": (["ab", "cd"], ["", ""]),
        }
    )
    assert c.parts["e"] == "#ffffff"
    assert c.parts["z"] == critters.PART_DEFAULTS["z"]  # untouched default survives


def test_front_walk_keeps_face_and_shuffles_feet():
    """A front-facing critter's walk reuses the idle face/torso (so the eyes stay in
    the head) and only animates the feet row."""
    c = critters.get("cat")
    idle = c.states["idle"][0]
    walk = c.states["walk"]
    for f in walk:
        assert f.art[:-1] == idle.art[:-1], "walk must keep the idle face/torso unchanged"
    assert len({f.art[-1] for f in walk}) > 1, "feet must shuffle across the walk cycle"


def test_walk_cycle_animates_feet():
    """The walk must actually move: a critter's walk frames are not all identical,
    and the motion is in the bottom (feet) row while the body stays put."""
    for name in critters.names():
        c = critters.get(name)
        frames = c.states["walk"]
        assert len(frames) >= 4, f"{name}: expected a multi-phase walk"
        bottoms = {f.art[-1] for f in frames}
        assert len(bottoms) > 1, f"{name}: feet never move"
        # every non-leg row is identical across the cycle (body doesn't jitter)
        for r in range(c.height - 1):
            assert len({f.art[r] for f in frames}) == 1, f"{name}: body row {r} jitters"


def test_roster_has_expected_critters():
    """The roster is trimmed to four art-quality critters: cat, duck, possum, rabbit."""
    assert set(critters.names()) == {"cat", "duck", "possum", "rabbit"}


def test_walk_left_is_same_object_as_walk():
    """Critters face the viewer so walk_left must be the exact same tuple as
    states['walk'] — not merely shape-compatible but identity-equal (same object)."""
    for name in critters.names():
        c = critters.get(name)
        assert c.walk_left is c.states[critters.WALK], (
            f"{name}: walk_left should be the same object as states['walk']"
        )


def test_shift_clips_to_original_width():
    """_shift preserves the row width: it offsets characters and clips, never extends."""
    from buddy.critters import _shift  # private helper; tested here as the walk-derive crux

    assert _shift("abcd", 0) == "abcd"  # identity
    assert _shift("abcd", 2) == "  ab"  # shift right: prepend spaces, clip right end
    assert _shift("abcd", -2) == "cd  "  # shift left: drop prefix, pad right with spaces
    assert _shift("abcd", 99) == "    "  # extreme right: all spaces (clips fully)
    assert _shift("abcd", -99) == "    "  # extreme left: same result
