"""The Textual application: the animation loop, input bindings, and wiring.

Owns a seeded RNG (INV-3), a :class:`~buddy.events.NullReactor` by default (INV-5 —
no subprocess/network in the default run), and a :class:`~buddy.creature.Creature`
rendered by :class:`~buddy.stage.StageWidget`. The tick interval is started only
when ``config.animate`` is true, which lets snapshot tests render a fixed pose
deterministically.
"""

from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.css.query import NoMatches
from textual.widgets import Footer

from buddy import config, critters, events
from buddy.config import BuddyConfig
from buddy.creature import Creature
from buddy.stage import StageWidget

# Fallback stage size before the terminal reports its real dimensions.
_DEFAULT_COLS = 48
_DEFAULT_ROWS = 14


class BuddyApp(App):
    """The buddy companion app."""

    CSS = """
    StageWidget { width: 1fr; height: 1fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("space", "cycle", "Next critter"),
        ("t", "talk", "Talk"),
    ]

    def __init__(self, cfg: BuddyConfig | None = None) -> None:
        super().__init__()
        self.cfg = cfg or BuddyConfig()
        self.rng = random.Random(self.cfg.seed)
        if self.cfg.feeds:
            self.reactor = events.get_reactor(
                "feeds",
                feeds=self.cfg.feeds,
                latitude=self.cfg.latitude,
                longitude=self.cfg.longitude,
                user_agent=config.FEED_USER_AGENT,
            )
        else:
            self.reactor = events.get_reactor("null")  # INV-5: passive default
        self._names = critters.names()
        if self.cfg.animal == "random":
            self._idx = self.rng.randrange(len(self._names))
        else:
            self._idx = self._names.index(self.cfg.animal)
        self.creature: Creature | None = None

    # -- lifecycle -------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield StageWidget()
        yield Footer()

    def on_mount(self) -> None:
        cols = self.size.width or _DEFAULT_COLS
        rows = self.size.height or _DEFAULT_ROWS
        self.creature = self._new_creature(cols, rows)
        if self.cfg.animate:
            interval = 1.0 / (config.FPS * self.cfg.speed)
            self.set_interval(interval, self._tick)

    def on_unmount(self) -> None:
        """Stop the feed reactor's background thread on shutdown, if any."""
        close = getattr(self.reactor, "close", None)
        if close is not None:
            close()

    def on_resize(self, event) -> None:
        if self.creature is not None:
            self.creature.resize(event.size.width, event.size.height)
            self._refresh_stage()

    # -- animation -------------------------------------------------------

    def _tick(self) -> None:
        if self.creature is None:  # interval could fire before on_mount finishes
            return
        self.creature.tick(self.reactor.poll())
        self._refresh_stage()

    def _refresh_stage(self) -> None:
        try:
            self.query_one(StageWidget).refresh()
        except NoMatches:  # stage not mounted yet (e.g. a tick before on_mount)
            pass

    def _new_creature(self, cols: int, rows: int) -> Creature:
        critter = critters.get(self._names[self._idx])
        return Creature(critter, cols, rows, self.rng)

    # -- actions ---------------------------------------------------------

    def action_cycle(self) -> None:
        """Switch to the next critter, keeping the current stage size."""
        if self.creature is None:
            return
        self._idx = (self._idx + 1) % len(self._names)
        self.creature = self._new_creature(self.creature.cols, self.creature.rows)
        self._refresh_stage()

    def action_talk(self) -> None:
        """Pop a speech bubble on demand."""
        if self.creature is not None:
            self.creature.force_talk()
            self._refresh_stage()
