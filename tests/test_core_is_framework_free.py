"""INV-4 gate: the framework-free set imports no Textual, so the behavioral core
(and the pure renderer) stay unit-testable without a terminal.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "buddy"
FRAMEWORK_FREE = ["creature.py", "critters.py", "dialogue.py", "render.py"]


def _imported_modules(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


@pytest.mark.parametrize("filename", FRAMEWORK_FREE)
def test_core_module_imports_no_textual(filename):
    names = _imported_modules(SRC / filename)
    offenders = [n for n in names if n == "textual" or n.startswith("textual.")]
    assert not offenders, f"{filename} imports Textual: {offenders}"
