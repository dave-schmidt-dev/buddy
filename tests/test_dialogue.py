"""Tests for buddy.dialogue — behaviour-named, no fixtures needed."""

from __future__ import annotations

import random

import pytest

from buddy import critters
from buddy.config import MAX_BUBBLE_WIDTH
from buddy.dialogue import CATEGORIES, DIALOGUE, SPECIES, all_lines, pick, speak

_GENERAL = {line for c in CATEGORIES for line in DIALOGUE[c]}


def test_every_category_pool_is_non_empty() -> None:
    """Each category in CATEGORIES must have at least one line."""
    for category in CATEGORIES:
        assert category in DIALOGUE, f"Category {category!r} missing from DIALOGUE"
        assert len(DIALOGUE[category]) >= 1, f"Category {category!r} is empty"


def test_every_line_within_bubble_width() -> None:
    """No line may exceed MAX_BUBBLE_WIDTH characters."""
    violations = [(line, len(line)) for line in all_lines() if len(line) > MAX_BUBBLE_WIDTH]
    assert violations == [], f"Lines exceed {MAX_BUBBLE_WIDTH} chars: {violations}"


def test_pick_is_deterministic_under_seed() -> None:
    """Same seed produces the same pick; two independent RNGs agree."""
    result_a = pick(random.Random(0), "tips")
    result_b = pick(random.Random(0), "tips")
    assert result_a == result_b

    rng1 = random.Random(42)
    rng2 = random.Random(42)
    sequence_1 = [pick(rng1, "tips") for _ in range(5)]
    sequence_2 = [pick(rng2, "tips") for _ in range(5)]
    assert sequence_1 == sequence_2


def test_pick_unknown_category_raises() -> None:
    """pick() with an unrecognised category raises ValueError."""
    with pytest.raises(ValueError, match="bogus"):
        pick(random.Random(0), "bogus")


def test_pick_only_returns_lines_from_category() -> None:
    """pick() never returns a line from a different category."""
    for category in CATEGORIES:
        rng = random.Random(7)
        for _ in range(20):
            result = pick(rng, category)
            assert result in DIALOGUE[category], f"{result!r} not in DIALOGUE[{category!r}]"


def test_every_critter_has_species_lines() -> None:
    """SPECIES must cover exactly the roster, so every critter has its own flavor."""
    assert set(SPECIES) == set(critters.names())
    for name, lines in SPECIES.items():
        assert lines, f"{name} has no species lines"


def test_speak_only_returns_known_lines() -> None:
    """Anything a critter says must come from a known pool (general or its species)."""
    pool = set(all_lines())
    rng = random.Random(1)
    for _ in range(300):
        assert speak(rng, "cat") in pool


def test_speak_mixes_species_and_general() -> None:
    """Over many draws a critter says both its own lines and general ones."""
    rng = random.Random(2)
    said = [speak(rng, "dog") for _ in range(400)]
    assert any(s in set(SPECIES["dog"]) for s in said), "should say species lines"
    assert any(s in _GENERAL for s in said), "should also say general lines"


def test_speak_is_deterministic_under_seed() -> None:
    """Same seed -> same sequence (INV-3)."""
    seq1 = [speak(random.Random(9), "duck")]
    r1, r2 = random.Random(9), random.Random(9)
    assert [speak(r1, "duck") for _ in range(10)] == [speak(r2, "duck") for _ in range(10)]
    assert seq1  # sanity: at least one line produced


def test_speak_unknown_critter_falls_back_to_general() -> None:
    """A name with no species pool draws only from the general pools."""
    rng = random.Random(3)
    for _ in range(50):
        assert speak(rng, "dragon") in _GENERAL
