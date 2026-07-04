"""The creature state machine — pure, framework-free behavioral core (INV-4).

A :class:`Creature` owns the critter's position, pose, animation frame, and speech
bubble, and advances them one :meth:`tick` at a time. ALL randomness flows through
an injected :class:`random.Random` (INV-3): construct two creatures with the same
seed and they produce byte-identical runs, which is what makes the behavior
provable and the snapshots stable.

Poses are the four critter art states (walk/idle/blink/nap). "Talk" is modeled as
an independent bubble overlay, not a pose, so a critter can talk while walking or
standing without needing dedicated art.
"""

from __future__ import annotations

import collections
import random

from buddy import config, dialogue
from buddy.critters import BLINK, IDLE, NAP, WALK, Critter, Frame

# Poses the creature can be in (subset of critter art states).
_POSES = (WALK, IDLE, BLINK, NAP)


class Creature:
    """Stateful, deterministic animation model for one critter on a stage.

    Args:
        critter: The :class:`~buddy.critters.Critter` art to animate.
        cols: Stage width in columns.
        rows: Stage height in rows.
        rng: Injected RNG. When *None*, an unseeded ``random.Random()`` is used.

    Attributes are plain and public so tests can pin state directly.
    """

    def __init__(
        self,
        critter: Critter,
        cols: int,
        rows: int,
        rng: random.Random | None = None,
    ) -> None:
        self.critter = critter
        self.cols = cols
        self.rows = rows
        self.rng = rng if rng is not None else random.Random()

        # Horizontal travel range: sprite left edge in [0, max_x].
        self.max_x = max(0, cols - critter.width)
        # Base top row so the sprite stands just above the ground (bottom) line.
        self.base_y = max(0, rows - 1 - critter.height)

        self.x = self.max_x // 2
        self.y = self.base_y
        self.dx = self.rng.choice((-1, 1))

        self.state = IDLE
        self.prev_pose = IDLE  # pose to restore after a blink
        self.state_timer = self._duration(IDLE)
        self.frame_index = 0
        self.frame_timer = config.FRAME_ADVANCE_TICKS
        self.bob = 0  # vertical bob offset (0 or 1), applied while walking
        self.turn_pause = 0  # frames to hold at a wall before walking back
        self.anim_clock = 0  # monotonic tick counter driving ambient breathing

        self.message: str | None = None
        self.bubble_timer = 0
        self._ambient: collections.deque[str] = collections.deque(maxlen=8)
        self._pending_alert: str | None = None
        self._pending_alert_level: str | None = None
        self._alert_level: str | None = None
        self._preempted_alert_ids: set[str] = set()

    # -- durations -------------------------------------------------------

    def _duration(self, pose: str) -> int:
        if pose == WALK:
            return self.rng.randint(*config.WALK_TICKS_RANGE)
        if pose == IDLE:
            return self.rng.randint(*config.IDLE_TICKS_RANGE)
        if pose == NAP:
            return config.NAP_TICKS
        if pose == BLINK:
            return config.BLINK_TICKS
        return 1

    # -- frames ----------------------------------------------------------

    def current_frame(self) -> Frame:
        """Return the art+mask frame for the current pose and animation index.

        Walk frames face the travel direction (``dx``); front poses ignore it.
        """
        return self.critter.frame(self.state, self.frame_index, facing_left=self.dx < 0)

    def sprite_y(self) -> int:
        """Top row at which to draw the sprite this tick (bob + breath, clamped)."""
        return max(0, self.y - self.bob - self._breath())

    def _breath(self) -> int:
        """A slow 1-row lift while standing/napping, so the critter looks alive.

        Held for the tail of each breath cycle. Clock 0 yields 0, which keeps pinned
        snapshots (captured without ticking) stable.
        """
        if self.state == WALK:
            return 0
        phase = self.anim_clock % config.BREATH_PERIOD
        return 1 if phase >= config.BREATH_PERIOD - config.BREATH_HOLD else 0

    # -- the tick --------------------------------------------------------

    def tick(self, events=()) -> None:
        """Advance the model one frame.

        ``events`` is a sequence of :class:`buddy.events.Event` objects emitted by
        ambient feed reactors this tick. Events are routed via :meth:`_route_events`
        before the bubble and pose updates so their effects land in the same tick.
        """
        self.anim_clock += 1
        self._route_events(events)
        self._update_bubble()
        self._update_pose()
        self._advance_frame()

    def _route_events(self, events) -> None:
        for ev in events:
            data = ev.data or {}
            text = data.get("text", "")
            if ev.kind == "nws.alert" and data.get("severity") in config.PREEMPT_SEVERITIES:
                alert_id = data.get("id")
                if alert_id in self._preempted_alert_ids:
                    continue
                self._preempted_alert_ids.add(alert_id)
                severity = data.get("severity")
                formatted = dialogue.format_feed_line(text)
                if self._pending_alert is None:
                    self._pending_alert = formatted
                    self._pending_alert_level = severity
                    if self.state == NAP:
                        self._enter(IDLE)  # a severe alert wakes a napping critter
                else:
                    self._ambient.append(formatted)  # second severe alert this tick — don't lose it
            elif text:
                self._ambient.append(dialogue.format_feed_line(text))

    def _update_bubble(self) -> None:
        if self._pending_alert is not None:
            self.message = self._pending_alert
            self.bubble_timer = config.ALERT_BUBBLE_TICKS
            self._alert_level = self._pending_alert_level
            self._pending_alert = None
            self._pending_alert_level = None
            return
        if self.message is not None:
            self.bubble_timer -= 1
            if self.bubble_timer <= 0:
                self.message = None
                self._alert_level = None
        elif self.state != NAP and self.rng.random() < config.TALK_PROB:
            if self._ambient and self.rng.random() < config.FEED_MIX:
                self.message = self._ambient.popleft()
            else:
                self.message = dialogue.speak(self.rng, self.critter.name)
            self.bubble_timer = config.BUBBLE_TICKS

    def _update_pose(self) -> None:
        if self.state == BLINK:
            self.state_timer -= 1
            if self.state_timer <= 0:
                self._enter(self.prev_pose)
            return
        if self.state == NAP:
            self.state_timer -= 1
            if self.state_timer <= 0:
                self._enter(IDLE)
            return

        # WALK or IDLE: chance to blink or nap, else count down and swap.
        if self.rng.random() < config.BLINK_PROB:
            self.prev_pose = self.state
            self._enter(BLINK)
            return
        if self._alert_level is None and self.rng.random() < config.NAP_PROB:
            self._enter(NAP)
            return
        self.state_timer -= 1
        if self.state_timer <= 0:
            self._enter(WALK if self.state == IDLE else IDLE)

    def _enter(self, pose: str) -> None:
        self.state = pose
        self.state_timer = self._duration(pose)
        self.frame_index = 0
        self.frame_timer = config.FRAME_ADVANCE_TICKS
        if pose != WALK:
            self.bob = 0
        if pose == NAP:
            # A critter shouldn't keep talking once it dozes off. Bubbles are set
            # earlier in the same tick (in _update_bubble), so clear any here.
            self.message = None
            self.bubble_timer = 0

    def _walk(self) -> None:
        """Take one step, or spend one frame of the turn-around pause at a wall."""
        if self.turn_pause > 0:
            self.turn_pause -= 1
            return
        self.x += self.dx * config.WALK_STEP
        if self.x <= 0:
            self.x = 0
            self.dx = 1
            self.turn_pause = config.TURN_PAUSE_FRAMES
        elif self.x >= self.max_x:
            self.x = self.max_x
            self.dx = -1
            self.turn_pause = config.TURN_PAUSE_FRAMES

    def _advance_frame(self) -> None:
        # Step once per leg-frame so footfalls land with the stride (not a glide).
        self.frame_timer -= 1
        if self.frame_timer <= 0:
            self.frame_timer = config.FRAME_ADVANCE_TICKS
            if self.state == WALK:
                self._walk()
            self.frame_index += 1
        if self.state == WALK:
            self.bob = self.frame_index % 2

    # -- external controls (used by the app view) ------------------------

    def resize(self, cols: int, rows: int) -> None:
        """Adapt to a new stage size, keeping the critter in bounds."""
        self.cols = cols
        self.rows = rows
        self.max_x = max(0, cols - self.critter.width)
        self.base_y = max(0, rows - 1 - self.critter.height)
        self.x = min(self.x, self.max_x)
        self.y = self.base_y

    def force_talk(self) -> None:
        """Immediately show a dialogue bubble (bound to a key press)."""
        self.message = dialogue.speak(self.rng, self.critter.name)
        self.bubble_timer = config.BUBBLE_TICKS

    # -- introspection (for tests / rendering) ---------------------------

    def snapshot(self) -> tuple:
        """A hashable summary of the visible state, for determinism tests."""
        return (self.state, self.x, self.sprite_y(), self.frame_index, self.message)

    @property
    def alert_level(self) -> str | None:
        """Severity ("Extreme"/"Severe") of the currently shown alert bubble, else None.
        The view uses this to color alert bubbles distinctly from ordinary speech."""
        return self._alert_level
