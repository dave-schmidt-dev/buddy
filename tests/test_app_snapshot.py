"""TUI visual-regression via SVG snapshots. Deterministic by construction:
animate=False means no interval starts, and run_before pins the creature to a fixed
pose/position before capture. Color is captured too, so the palette is regression-
tested for free. Regenerate baselines with: pytest --snapshot-update
"""

from __future__ import annotations

from buddy.app import BuddyApp
from buddy.config import BuddyConfig


def _pin(state: str, x: int, message: str | None = None):
    def run_before(pilot) -> None:
        c = pilot.app.creature
        c.state = state
        c.x = x
        c.y = c.base_y
        c.frame_index = 0
        c.bob = 0
        c.anim_clock = 0  # no breath lift -> stable capture
        c.message = message
        pilot.app._refresh_stage()

    return run_before


def test_snapshot_cat_idle(snap_compare):
    app = BuddyApp(BuddyConfig(animal="cat", animate=False, seed=1))
    assert snap_compare(app, terminal_size=(40, 12), run_before=_pin("idle", 8))


def test_snapshot_duck_talking(snap_compare):
    app = BuddyApp(BuddyConfig(animal="duck", animate=False, seed=1))
    assert snap_compare(
        app, terminal_size=(44, 12), run_before=_pin("idle", 10, message="commit early")
    )
