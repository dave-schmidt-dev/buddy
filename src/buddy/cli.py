"""Command-line interface for buddy.

Entry points
------------
- ``buddy`` console script  →  :func:`main`
- ``python -m buddy``       →  :mod:`buddy.__main__`
"""

from __future__ import annotations

import argparse

from buddy import critters
from buddy.config import SPEED_MAX, SPEED_MIN, BuddyConfig
from buddy.logging_config import setup_logging


def positive_speed(s: str) -> float:
    """Parse and validate the ``--speed`` argument.

    Args:
        s: Raw string value from the command line.

    Returns:
        Validated float speed value.

    Raises:
        argparse.ArgumentTypeError: If the value is not a number or out of range.
    """
    try:
        value = float(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"--speed must be a number, got: {s!r}") from None

    if not (SPEED_MIN < value <= SPEED_MAX):
        raise argparse.ArgumentTypeError(
            f"--speed must be in ({SPEED_MIN}, {SPEED_MAX}], got {value}"
        )
    return value


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser` instance.
    """
    parser = argparse.ArgumentParser(
        prog="buddy",
        description="An ambient ASCII-art coding companion for your terminal.",
    )
    parser.add_argument(
        "--animal",
        default="random",
        choices=[*critters.names(), "random"],
        metavar="CRITTER",
        help="Which critter to display: %(choices)s (default: random).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available critters and exit.",
    )
    parser.add_argument(
        "--speed",
        type=positive_speed,
        default=1.0,
        metavar="SPEED",
        help=f"Animation speed multiplier ({SPEED_MIN} < SPEED <= {SPEED_MAX}, default: 1.0).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="N",
        help="Integer RNG seed for reproducible behaviour.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG-level logging to log file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and launch buddy.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]`` when *None*).

    Returns:
        Integer exit code (0 = success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_logging(args.debug)

    if args.list:
        print("Critters: " + ", ".join(critters.names()) + ", random")
        return 0

    cfg = BuddyConfig(
        animal=args.animal,
        speed=args.speed,
        seed=args.seed,
        debug=args.debug,
    )

    # Import the Textual app lazily so --list / --help stay framework-free and fast.
    from buddy.app import BuddyApp

    BuddyApp(cfg).run()
    return 0
