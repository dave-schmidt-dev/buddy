"""INV-5 gate: the default run performs no subprocess or network I/O. Tested at
the real entry point (the running app), not just an internal seam.

Three layers:
  (a) the default reactor is NullReactor,
  (b) a full default app run touches neither subprocess nor socket,
  (c) no default-path module imports subprocess/socket at module top level
      (the opt-in reactor stubs import them lazily inside methods only).
"""

from __future__ import annotations

import ast
import asyncio
import pathlib

import pytest

from buddy.app import BuddyApp
from buddy.config import BuddyConfig
from buddy.events import NullReactor

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "buddy"

# Every buddy module that must stay import-passive. INV-5's area is src/buddy/**,
# so this covers the default no-flag run path PLUS devsheet (a separate entry point
# that must not shell out either). events.py is included too: its reactor stubs
# import subprocess/os lazily INSIDE methods, so the module top stays clean.
DEFAULT_PATH_MODULES = [
    "__init__.py",
    "__main__.py",
    "cli.py",
    "config.py",
    "logging_config.py",
    "events.py",
    "creature.py",
    "critters.py",
    "dialogue.py",
    "render.py",
    "stage.py",
    "app.py",
    "devsheet.py",
]


def test_default_reactor_is_null():
    assert isinstance(BuddyApp(BuddyConfig()).reactor, NullReactor)


def test_default_run_uses_no_subprocess_or_socket(monkeypatch):
    """Patch AFTER the event loop exists (asyncio's own self-pipe uses socket), so
    any trip is buddy's, then drive the real app for a spell of ticks."""

    def boom(*args, **kwargs):
        raise AssertionError("INV-5 violation: default run used subprocess/socket")

    async def run() -> None:
        import socket
        import subprocess

        monkeypatch.setattr(subprocess, "Popen", boom)
        monkeypatch.setattr(subprocess, "run", boom)
        monkeypatch.setattr(socket, "socket", boom)

        app = BuddyApp(BuddyConfig(seed=1, animal="cat", speed=1.0))
        async with app.run_test(size=(48, 14)) as pilot:
            for _ in range(20):
                await pilot.pause()

    asyncio.run(run())


def _toplevel_imports(path: pathlib.Path) -> list[str]:
    """Module-level imports only (not those nested inside functions/methods)."""
    tree = ast.parse(path.read_text())
    names: list[str] = []
    for node in tree.body:  # top level only
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


@pytest.mark.parametrize("filename", DEFAULT_PATH_MODULES)
def test_default_path_module_has_no_toplevel_subprocess_or_socket(filename):
    names = _toplevel_imports(SRC / filename)
    offenders = [n for n in names if n in ("subprocess", "socket")]
    assert not offenders, f"{filename} imports {offenders} at module top level"
