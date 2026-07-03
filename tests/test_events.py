"""Tests for the buddy.events reactor seam."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from buddy.events import NullReactor, get_reactor

# Absolute path to src/ so the fresh-interpreter subprocess can import buddy
# without requiring an editable install.
_SRC_DIR = str(Path(__file__).parent.parent / "src")


def test_null_reactor_polls_empty() -> None:
    """NullReactor.poll() must return an empty list — no events, no I/O."""
    assert NullReactor().poll() == []


def test_default_reactor_is_null() -> None:
    """get_reactor() with no arguments must return a NullReactor instance."""
    assert isinstance(get_reactor(), NullReactor)


def test_get_reactor_unknown_raises() -> None:
    """get_reactor() with an unrecognised name must raise ValueError."""
    with pytest.raises(ValueError, match="bogus"):
        get_reactor("bogus")


def test_importing_events_does_not_import_subprocess_or_socket() -> None:
    """Importing buddy.events must NOT pull subprocess or socket into sys.modules.

    This enforces INV-5: the default run path is fully passive.  The check
    runs in a fresh interpreter so this test file's own subprocess import
    cannot contaminate the result.
    """
    env = {**os.environ, "PYTHONPATH": _SRC_DIR}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import buddy.events; "
                "assert 'subprocess' not in sys.modules and 'socket' not in sys.modules, "
                "'passive-import invariant violated: '"
                " + str([k for k in sys.modules if k in ('subprocess', 'socket')])"
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, (
        f"Module-top passive-import check failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
