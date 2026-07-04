"""INV-2 gate: the renderer clips all drawing to the grid and never raises, at any
pane size (down to 1x1) and any creature position. The pure compose_frame is tested
here without importing Textual.
"""

from __future__ import annotations

import random
import subprocess
import sys

import pytest

from buddy import config, critters
from buddy.creature import Creature
from buddy.events import Event
from buddy.render import K_ALERT, K_BUBBLE, K_GROUND, K_SPRITE, compose_frame


def _creature(cols=40, rows=12, animal="cat"):
    c = Creature(critters.get(animal), cols, rows, random.Random(0))
    c.state = "idle"
    c.frame_index = 0
    c.bob = 0
    return c


@pytest.mark.parametrize(
    "cols,rows",
    [(40, 12), (24, 8), (23, 8), (40, 7), (10, 10), (1, 1), (0, 0), (3, 3)],
)
def test_output_dimensions_are_exact(cols, rows):
    """rows/kinds are always exactly rows strings of exactly cols chars."""
    r = compose_frame(_creature(cols, rows), cols, rows)
    assert len(r.rows) == rows
    assert len(r.kinds) == rows
    for line in r.rows:
        assert len(line) == cols
    for line in r.kinds:
        assert len(line) == cols


@pytest.mark.parametrize("x,y", [(-5, 0), (100, 0), (0, -4), (0, 100), (-3, -3), (38, 10)])
def test_never_raises_with_sprite_off_edges(x, y):
    c = _creature(40, 12)
    c.x, c.y, c.bob = x, y, 0
    r = compose_frame(c, 40, 12)  # must not raise
    assert len(r.rows) == 12 and all(len(line) == 40 for line in r.rows)


def test_sprite_cells_land_at_expected_clipped_coords():
    c = _creature(40, 12)
    c.x, c.y, c.bob = 5, 2, 0
    r = compose_frame(c, 40, 12)
    # cat idle row 1 "=( o.o )=": the '=' ear at frame col 0 -> grid (row 3, col 5),
    # and its mask marks an accent cell ('a'), not the plain body.
    assert r.rows[3][5] == "="
    assert r.kinds[3][5] == "a"
    # a body cell: idle row 3 " (_____) "; '(' at frame col 1 -> grid (row 5, col 6)
    assert r.rows[5][6] == "("
    assert r.kinds[5][6] == K_SPRITE


def test_ground_line_spans_bottom_row():
    r = compose_frame(_creature(40, 12), 40, 12)
    assert set(r.kinds[-1]) == {K_GROUND}
    assert set(r.rows[-1]) == {"~"}


def test_below_minimum_shows_too_small_notice():
    r = compose_frame(_creature(20, 10), 20, 10)
    assert any("small" in line for line in r.rows), "should show a 'too small' notice"
    assert K_BUBBLE in "".join(r.kinds)
    # no ground line in notice mode
    assert K_GROUND not in "".join(r.kinds)


def test_one_by_one_stage_does_not_crash():
    r = compose_frame(_creature(1, 1), 1, 1)
    assert len(r.rows) == 1 and len(r.rows[0]) == 1


def test_bubble_is_drawn_when_talking():
    c = _creature(40, 12)
    c.x, c.y, c.bob = 10, 6, 0
    c.message = "hi there"
    r = compose_frame(c, 40, 12)
    assert K_BUBBLE in "".join(r.kinds)
    assert "hi there" in "".join(r.rows)


def test_minimum_supported_size_renders_normally():
    """Exactly at the supported minimum, it renders the scene (not the notice)."""
    r = compose_frame(
        _creature(config.MIN_STAGE_COLS, config.MIN_STAGE_ROWS),
        config.MIN_STAGE_COLS,
        config.MIN_STAGE_ROWS,
    )
    assert K_GROUND in "".join(r.kinds)


def test_alert_bubble_tagged_and_marked():
    """Alert bubbles are tagged K_ALERT and contain '!' markers; K_BUBBLE must be absent."""
    c = _creature(40, 12)
    c.tick([Event("nws.alert", {"text": "Tornado Warning", "severity": "Extreme", "id": "a1"})])
    r = compose_frame(c, 40, 12)
    all_kinds = "".join(r.kinds)
    all_rows = "".join(r.rows)
    assert K_ALERT in all_kinds, "alert bubble cells must be tagged K_ALERT"
    assert "!" in all_rows, "alert bubble must contain '!' marker"
    assert K_BUBBLE not in all_kinds, "alert bubble must not be tagged K_BUBBLE"


def test_normal_bubble_tagged_bubble_kind():
    """A normal (non-alert) bubble is tagged K_BUBBLE, not K_ALERT."""
    c = _creature(40, 12)
    c.force_talk()
    r = compose_frame(c, 40, 12)
    all_kinds = "".join(r.kinds)
    assert K_BUBBLE in all_kinds, "normal bubble cells must be tagged K_BUBBLE"
    assert K_ALERT not in all_kinds, "normal bubble must not be tagged K_ALERT"


def test_render_module_imports_no_textual():
    """INV-4 support: importing the renderer must not pull in Textual."""
    import os
    import pathlib

    src_dir = str(pathlib.Path(__file__).resolve().parent.parent / "src")
    code = (
        "import sys; import buddy.render; "
        "assert 'textual' not in sys.modules, 'render imported textual'"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": src_dir},
    )
    assert proc.returncode == 0, proc.stderr
