"""INV-3 gate: the creature is deterministic under a seed, and its state machine
behaves (bounces at walls, wakes from naps, shows/clears bubbles). Determinism is
what makes behavior provable and snapshots stable.
"""

from __future__ import annotations

import random

from buddy import config, critters, dialogue
from buddy.creature import Creature
from buddy.critters import IDLE, NAP, WALK
from buddy.dialogue import format_feed_line
from buddy.events import Event


def _make(seed=42, cols=40, rows=12, animal="cat"):
    return Creature(critters.get(animal), cols, rows, random.Random(seed))


def test_same_seed_yields_identical_run():
    """INV-3: two creatures with the same seed produce byte-identical runs."""
    a = _make(seed=7)
    b = _make(seed=7)
    for _ in range(500):
        a.tick()
        b.tick()
        assert a.snapshot() == b.snapshot()


def test_different_seeds_diverge():
    """Sanity: different seeds should not lock-step (guards a hidden constant)."""
    a = _make(seed=1)
    b = _make(seed=2)
    seqs_equal = True
    for _ in range(500):
        a.tick()
        b.tick()
        if a.snapshot() != b.snapshot():
            seqs_equal = False
            break
    assert not seqs_equal


def test_walk_bounces_at_both_walls():
    c = _make()
    c.state = WALK
    c.x, c.dx, c.turn_pause = 0, -1, 0
    c._walk()
    assert c.x == 0 and c.dx == 1, "should bounce off the left wall"
    assert c.turn_pause == config.TURN_PAUSE_FRAMES, "a bounce arms the turn-around pause"
    c.x, c.dx, c.turn_pause = c.max_x, 1, 0
    c._walk()
    assert c.x == c.max_x and c.dx == -1, "should bounce off the right wall"


def test_turn_pause_holds_position_then_resumes():
    c = _make(cols=40)
    c.state = WALK
    c.x, c.dx, c.turn_pause = 10, 1, 3
    for _ in range(3):
        c._walk()  # paused frames: no movement, just drains the pause
        assert c.x == 10
    assert c.turn_pause == 0
    c._walk()
    assert c.x == 11, "after the pause the critter steps again"


def test_breath_lifts_while_idle_and_returns_to_zero_at_clock_zero():
    c = _make()
    c.state = IDLE
    c.anim_clock = 0
    assert c._breath() == 0, "clock 0 must not lift (keeps pinned snapshots stable)"
    lifts = set()
    for t in range(config.BREATH_PERIOD):
        c.anim_clock = t
        lifts.add(c._breath())
    assert lifts == {0, 1}, "breathing should toggle a single-row lift over a cycle"


def test_walking_critter_does_not_breathe():
    c = _make()
    c.state = WALK
    c.anim_clock = config.BREATH_PERIOD - 1  # inside the held tail of the cycle
    assert c._breath() == 0, "walk has its own bob; breathing is suppressed"


def test_position_stays_in_bounds_over_long_run():
    c = _make(cols=30, rows=10)
    for _ in range(2000):
        c.tick()
        assert 0 <= c.x <= c.max_x
        assert 0 <= c.sprite_y() < c.rows


def test_nap_wakes_to_idle():
    # The nap countdown draws no rng, so wakeup is exactly on tick NAP_TICKS and is
    # seed-independent. Ticking one MORE would let the now-idle creature re-roll
    # into another nap, which made this test seed-dependent before.
    c = _make()
    c._enter(NAP)
    assert c.state == NAP
    for _ in range(config.NAP_TICKS):
        c.tick()
    assert c.state == IDLE, "a nap must wake to idle exactly when its timer expires"


def test_entering_nap_clears_any_pending_bubble():
    """A bubble set on the same tick a nap begins must not linger while napping
    (regression: _update_bubble runs before the nap transition in the same tick)."""
    c = _make()
    c.message = "9 lives, 0 bugs"
    c.bubble_timer = config.BUBBLE_TICKS
    c._enter(NAP)
    assert c.state == NAP
    assert c.message is None, "a napping critter must not keep a speech bubble"
    assert c.bubble_timer == 0


def test_talk_bubble_clears_after_its_timer():
    c = _make()
    c.message = "hello there"
    c.bubble_timer = 1
    c._update_bubble()
    assert c.message is None, "bubble must clear when its timer expires"


def test_talk_fires_and_uses_valid_dialogue():
    c = _make(seed=3)
    seen = set()
    for _ in range(3000):
        c.tick()
        if c.message is not None:
            seen.add(c.message)
    assert seen, "over a long run the critter should talk at least once"
    assert seen <= set(dialogue.all_lines()), "messages must come from the dialogue pools"


def test_blink_returns_to_prior_pose():
    # Blink countdown is rng-free too: restore is exactly on tick BLINK_TICKS.
    c = _make()
    c.state = WALK
    c.prev_pose = WALK
    c._enter("blink")
    for _ in range(config.BLINK_TICKS):
        c.tick()
    assert c.state == WALK, "after blinking the critter resumes its prior pose"


def test_unseeded_creature_runs_without_error():
    c = Creature(critters.get("duck"), 40, 12)  # no rng injected
    for _ in range(50):
        c.tick()


def test_tiny_stage_keeps_creature_pinned_in_bounds():
    """Stage narrower than the sprite: max_x clamps to 0, no negative positions."""
    c = _make(cols=3, rows=3, animal="capybara")
    assert c.max_x == 0
    for _ in range(200):
        c.tick()
        assert c.x == 0
        assert 0 <= c.sprite_y() < c.rows


def test_footfall_advances_x_once_per_leg_frame():
    """x must advance exactly once per FRAME_ADVANCE_TICKS calls to _advance_frame,
    not on every call — the stride is locked to the leg animation, not the clock."""
    c = _make(cols=80)
    c.state = WALK
    c.dx = 1
    c.turn_pause = 0
    c.frame_timer = config.FRAME_ADVANCE_TICKS  # fresh timer, same as after any step
    x0 = c.x
    # calls before the timer fires: x must not move
    for _ in range(config.FRAME_ADVANCE_TICKS - 1):
        c._advance_frame()
        assert c.x == x0, "x must not advance before the leg frame fires"
    # the final call drains the timer to 0 and fires the step
    c._advance_frame()
    assert c.x == x0 + config.WALK_STEP, "x must advance exactly when the leg frame fires"
    # timer is reset; the very next call must not step
    c._advance_frame()
    assert c.x == x0 + config.WALK_STEP, "x must not advance on the first tick of the new frame"


def test_resize_updates_bounds_and_clamps_position():
    """resize() must recalculate max_x/base_y and bring x back inside the new stage."""
    c = _make(cols=80, rows=20)
    c.x = 60  # somewhere valid in the wide stage
    cat_width = c.critter.width
    c.resize(cols=30, rows=15)
    expected_max_x = max(0, 30 - cat_width)
    assert c.max_x == expected_max_x
    assert c.x <= c.max_x, "x must be clamped to the narrower stage"
    assert c.y == c.base_y, "y must be pinned to the new base_y"


def test_force_talk_immediately_sets_bubble():
    """force_talk() must post a message right now without waiting for a tick."""
    c = _make()
    assert c.message is None
    c.force_talk()
    assert c.message is not None, "message must be set immediately"
    assert c.bubble_timer == config.BUBBLE_TICKS, "timer must be armed to the full duration"
    assert c.message in set(dialogue.all_lines()), "message must come from a known pool"


def test_napping_critter_breathes():
    """NAP is not WALK — the breath lift must apply while napping too."""
    c = _make()
    c.state = NAP
    # set anim_clock to the held tail of the breath cycle
    c.anim_clock = config.BREATH_PERIOD - 1
    assert c._breath() == 1, "a napping critter should lift during the breath hold"
    # and return to 0 outside the held tail
    c.anim_clock = 0
    assert c._breath() == 0, "breath must be 0 at clock 0 even while napping"


# ---------------------------------------------------------------------------
# Ambient feed / event routing tests
# ---------------------------------------------------------------------------


def test_severe_alert_preempts_active_bubble():
    """A Severe alert replaces an in-progress bubble with the alert text."""
    c = _make()
    c.message = "old"
    c.bubble_timer = 5
    c.tick([Event("nws.alert", {"text": "Tornado Warning", "severity": "Severe", "id": "a1"})])
    assert c.message == format_feed_line("Tornado Warning")
    assert c.bubble_timer == config.ALERT_BUBBLE_TICKS


def test_severe_alert_wakes_napping_critter():
    """A Severe alert forces a napping critter into IDLE and shows the message."""
    c = _make()
    c.state = NAP
    c.tick([Event("nws.alert", {"text": "Tornado Warning", "severity": "Severe", "id": "w1"})])
    assert c.state != NAP
    assert c.message == format_feed_line("Tornado Warning")


def test_minor_alert_does_not_preempt():
    """A Minor alert is queued in _ambient, not in _pending_alert."""
    c = _make()
    c.tick([Event("nws.alert", {"text": "Frost Advisory", "severity": "Minor", "id": "m1"})])
    assert c._pending_alert is None
    assert format_feed_line("Frost Advisory") in list(c._ambient)


def test_repeated_severe_alert_preempts_once():
    """The same severe alert id must not preempt a second time (id remembered)."""
    c = _make()
    c.tick([Event("nws.alert", {"text": "Tornado Warning", "severity": "Severe", "id": "dup1"})])
    first_message = c.message
    assert first_message == format_feed_line("Tornado Warning")
    # Clear the bubble so we can detect a second preemption
    c.message = None
    c.bubble_timer = 0
    c.tick([Event("nws.alert", {"text": "Tornado Warning", "severity": "Severe", "id": "dup1"})])
    # Second tick with same id must NOT re-preempt
    assert c.message is None or c.message != format_feed_line("Tornado Warning")
    assert "dup1" in c._preempted_alert_ids


def test_ambient_headline_surfaces_in_rotation(monkeypatch):
    """With TALK_PROB=1.0 and FEED_MIX=1.0, an ambient headline is shown next tick."""
    monkeypatch.setattr(config, "TALK_PROB", 1.0)
    monkeypatch.setattr(config, "FEED_MIX", 1.0)
    c = _make()
    c.state = IDLE
    c.message = None
    headline = format_feed_line("Breaking: tests are passing")
    c._ambient.append(headline)
    c.tick([])
    assert c.message == headline


def test_second_severe_alert_same_tick_goes_to_ambient():
    """Fix A: a second distinct severe alert in the same tick must not be lost."""
    c = _make()
    c.tick(
        [
            Event("nws.alert", {"text": "Tornado Warning", "severity": "Severe", "id": "a1"}),
            Event("nws.alert", {"text": "Flash Flood Warning", "severity": "Severe", "id": "a2"}),
        ]
    )
    assert c.message == format_feed_line("Tornado Warning"), "first alert must preempt"
    assert format_feed_line("Flash Flood Warning") in list(c._ambient), (
        "second alert must be queued in _ambient, not dropped"
    )


def test_alert_bubble_survives_forced_nap(monkeypatch):
    """Fix B: _alert_level blocks the NAP transition so the alert bubble is not cleared."""
    c = _make()
    c.tick([Event("nws.alert", {"text": "Tornado Warning", "severity": "Severe", "id": "sn1"})])
    assert c.message is not None
    assert c.alert_level == "Severe"
    alert_text = c.message
    monkeypatch.setattr(config, "NAP_PROB", 1.0)
    monkeypatch.setattr(config, "BLINK_PROB", 0.0)
    c.tick([])
    assert c.state != NAP, "critter must not nap while an alert is showing"
    assert c.message == alert_text, "alert bubble must survive when nap is blocked"


def test_alert_level_tracks_severity():
    """alert_level reflects the severity of the active alert, then clears on expiry."""
    c = _make()
    assert c.alert_level is None
    # Extreme alert shows — alert_level must be "Extreme"
    c.tick([Event("nws.alert", {"text": "Major Hurricane", "severity": "Extreme", "id": "ext1"})])
    assert c.alert_level == "Extreme"
    # Expire the bubble by running _update_bubble with timer at 1
    c.bubble_timer = 1
    c._update_bubble()
    assert c.alert_level is None, "alert_level must clear when the bubble expires"
    # Severe alert shows — alert_level must be "Severe"
    c.tick([Event("nws.alert", {"text": "Tornado Warning", "severity": "Severe", "id": "sev1"})])
    assert c.alert_level == "Severe"


def test_scripted_event_stream_is_deterministic():
    """INV-3: two creatures with the same seed produce identical output under identical events."""
    a = _make(seed=77)
    b = _make(seed=77)
    # Build a deterministic per-tick event schedule (40 ticks)
    per_tick_events = [[] for _ in range(40)]
    per_tick_events[5] = [Event("feed.headline", {"text": "Story one", "id": 1})]
    per_tick_events[10] = [Event("weather.now", {"text": "Sunny skies"})]
    per_tick_events[15] = [
        Event("nws.alert", {"text": "Flash Flood Warning", "severity": "Severe", "id": "ff1"})
    ]
    per_tick_events[25] = [Event("feed.headline", {"text": "Story two", "id": 2})]
    messages_a = []
    messages_b = []
    for evs in per_tick_events:
        a.tick(evs)
        b.tick(evs)
        messages_a.append(a.message)
        messages_b.append(b.message)
    assert messages_a == messages_b, "event-driven runs must be byte-identical under same seed"
