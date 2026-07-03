"""Event types and reactor protocol for buddy's ambient reactivity seam.

v1 ships this inert: the default reactor is NullReactor, which performs
no I/O whatsoever.  Future opt-in reactors (GitReactor, FileWatchReactor)
are stubs here and will be filled in when needed.

INV-4: no textual import.
INV-5: no subprocess or socket at module top level — the default run path
       must remain fully passive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Event:
    """A single ambient event emitted by a Reactor.

    Attributes:
        kind: Short identifier for the event type (e.g. ``"git.dirty"``).
        data: Optional free-form payload; defaults to None.
    """

    kind: str
    data: dict | None = field(default=None)


class Reactor(Protocol):
    """Interface for ambient event sources.

    Return events observed since the last poll; [] when nothing happened.
    """

    def poll(self) -> list[Event]:
        """Return events observed since the last poll; [] when nothing happened."""
        ...


class NullReactor:
    """The v1 default reactor.  Fully passive — never emits events, never
    performs any I/O.
    """

    def poll(self) -> list[Event]:
        """Return an empty list; NullReactor is always silent.

        Returns:
            An empty list.
        """
        return []


class GitReactor:
    """Future opt-in reactor that will poll ``git status`` for dirty-state events.

    This is an INERT stub.  The lazy ``import subprocess`` inside ``poll``
    proves the pattern — module import of ``buddy.events`` never pulls
    subprocess into ``sys.modules``.

    Do not activate until the polling interval and event schema are finalised.
    """

    def poll(self) -> list[Event]:
        """Return events observed since the last poll; [] when nothing happened.

        Raises:
            NotImplementedError: Always; reactor is not yet implemented.
        """
        import subprocess  # noqa: F401  # lazy — keeps module-top clean (INV-5)

        raise NotImplementedError("GitReactor is not yet implemented")


class FileWatchReactor:
    """Future opt-in reactor that will watch for filesystem changes.

    This is an INERT stub.  The lazy ``import`` pattern mirrors GitReactor.
    """

    def poll(self) -> list[Event]:
        """Return events observed since the last poll; [] when nothing happened.

        Raises:
            NotImplementedError: Always; reactor is not yet implemented.
        """
        import os  # noqa: F401  # lazy placeholder for future inotify/kqueue usage

        raise NotImplementedError("FileWatchReactor is not yet implemented")


def get_reactor(name: str = "null") -> Reactor:
    """Factory that returns a Reactor instance by name.

    v1's CLI always passes ``"null"``.  Other names are reserved for future
    opt-in use; they are registered here so callers get a clear ValueError
    rather than a silent fallback.

    Args:
        name: One of ``"null"``, ``"git"``, or ``"filewatch"``.

    Returns:
        A Reactor instance matching *name*.

    Raises:
        ValueError: If *name* is not a recognised reactor name.
    """
    match name:
        case "null":
            return NullReactor()
        case "git":
            return GitReactor()
        case "filewatch":
            return FileWatchReactor()
        case _:
            raise ValueError(f"Unknown reactor name: {name!r}")
