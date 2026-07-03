"""Tests for BuddyApp interactive actions and lifecycle.

Uses asyncio.run() + Textual's run_test() pilot — same pattern as
test_default_is_passive.py.  All tests use animate=False so the tick interval
is never started, keeping behaviour deterministic between pauses.
"""

from __future__ import annotations

import asyncio

from buddy.app import BuddyApp
from buddy.config import BuddyConfig


def test_action_cycle_changes_critter():
    """Pressing space replaces the creature with the next critter in the roster."""

    async def run() -> None:
        app = BuddyApp(BuddyConfig(animate=False, seed=1, animal="cat"))
        async with app.run_test(size=(48, 14)) as pilot:
            await pilot.pause()
            original_name = app.creature.critter.name
            await pilot.press("space")
            await pilot.pause()
            assert app.creature.critter.name != original_name

    asyncio.run(run())


def test_action_talk_sets_message():
    """Pressing 't' immediately populates the creature's speech-bubble message."""

    async def run() -> None:
        app = BuddyApp(BuddyConfig(animate=False, seed=1, animal="cat"))
        async with app.run_test(size=(48, 14)) as pilot:
            await pilot.pause()
            # Clear any message that might have appeared during mount.
            app.creature.message = None
            await pilot.press("t")
            await pilot.pause()
            assert app.creature.message is not None

    asyncio.run(run())


def test_resize_keeps_creature_in_bounds():
    """After a terminal shrink the creature's x stays within [0, max_x]."""

    async def run() -> None:
        app = BuddyApp(BuddyConfig(animate=False, seed=1, animal="cat"))
        async with app.run_test(size=(48, 14)) as pilot:
            await pilot.pause()
            # Pin creature to the far right so a shrink would push it out of bounds
            # if resize() didn't clamp.
            app.creature.x = app.creature.max_x
            await pilot.resize_terminal(30, 10)
            await pilot.pause()
            assert 0 <= app.creature.x <= app.creature.max_x

    asyncio.run(run())


def test_animate_false_creature_does_not_advance_on_pauses():
    """With animate=False no tick interval fires; creature state is frozen."""

    async def run() -> None:
        app = BuddyApp(BuddyConfig(animate=False, seed=42, animal="cat"))
        async with app.run_test(size=(48, 14)) as pilot:
            await pilot.pause()
            before = app.creature.snapshot()
            for _ in range(10):
                await pilot.pause()
            after = app.creature.snapshot()
            assert before == after, "creature advanced without the tick interval"

    asyncio.run(run())
