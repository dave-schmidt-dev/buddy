"""Command-line interface for buddy.

Entry points
------------
- ``buddy`` console script  →  :func:`main`
- ``python -m buddy``       →  :mod:`buddy.__main__`
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from buddy import critters
from buddy.config import FEED_HTTP_TIMEOUT_S, FEED_USER_AGENT, SPEED_MAX, SPEED_MIN, BuddyConfig
from buddy.logging_config import setup_logging

logger = logging.getLogger(__name__)


def _resolve_zip(zip_code: str) -> tuple[float, float]:
    """Resolve a US ZIP code to (latitude, longitude) via api.zippopotam.us (keyless).

    Network import is lazy so cli.py stays import-passive on the default path (INV-5).
    """
    import json
    import urllib.request

    url = f"https://api.zippopotam.us/us/{zip_code}"
    req = urllib.request.Request(url, headers={"User-Agent": FEED_USER_AGENT})
    with urllib.request.urlopen(req, timeout=FEED_HTTP_TIMEOUT_S) as resp:
        data = json.load(resp)
    place = data["places"][0]
    return float(place["latitude"]), float(place["longitude"])


def _load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from a local .env into os.environ (without overriding
    existing env vars). Best-effort: silently returns if the file is absent."""
    if path is None:
        path = Path(__file__).resolve().parents[2] / ".env"  # project root
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def feed_list(s: str) -> tuple[str, ...]:
    """Parse and validate the comma-separated --feeds argument.

    Args:
        s: Raw string value from the command line.

    Returns:
        Tuple of validated feed names.

    Raises:
        argparse.ArgumentTypeError: If any token is not a known feed name.
    """
    valid = {"hn", "weather", "nws"}
    feeds = tuple(f.strip() for f in s.split(",") if f.strip())
    bad = [f for f in feeds if f not in valid]
    if bad:
        raise argparse.ArgumentTypeError(
            f"--feeds: unknown feed(s) {bad}; choose from {sorted(valid)}"
        )
    return feeds


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
    parser.add_argument(
        "--feeds",
        type=feed_list,
        default=(),
        metavar="LIST",
        help=(
            "Comma-separated opt-in feeds from: hn,weather,nws (default: none = passive)."
            " Performs network I/O."
        ),
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=None,
        metavar="DEG",
        help="Latitude for weather/nws feeds.",
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=None,
        metavar="DEG",
        help="Longitude for weather/nws feeds.",
    )
    parser.add_argument(
        "--zip",
        type=str,
        default=None,
        metavar="ZIP",
        help=(
            "US ZIP code to derive --lat/--lon for weather/nws feeds"
            " (keyless geocode; opt-in network)."
        ),
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

    needs_location = "weather" in args.feeds or "nws" in args.feeds
    if needs_location:
        _load_dotenv()
        if args.lat is None and args.lon is None and args.zip is None:
            env_lat, env_lon, env_zip = (
                os.environ.get("BUDDY_LAT"),
                os.environ.get("BUDDY_LON"),
                os.environ.get("BUDDY_ZIP"),
            )
            if env_zip:
                args.zip = env_zip
            elif env_lat and env_lon:
                args.lat, args.lon = float(env_lat), float(env_lon)
        if args.zip and (args.lat is None or args.lon is None):
            try:
                args.lat, args.lon = _resolve_zip(args.zip)
            except Exception as exc:  # noqa: BLE001 - resolution failure degrades, not fatal
                logger.warning(
                    "could not resolve zip %r (%s); weather/nws will be skipped", args.zip, exc
                )
        if args.lat is None or args.lon is None:
            dropped = tuple(f for f in ("weather", "nws") if f in args.feeds)
            args.feeds = tuple(f for f in args.feeds if f not in ("weather", "nws"))
            logger.warning(
                "no location for feed(s) %s; skipping them "
                "(set BUDDY_ZIP in .env or pass --lat/--lon/--zip)",
                ", ".join(dropped),
            )

    cfg = BuddyConfig(
        animal=args.animal,
        speed=args.speed,
        seed=args.seed,
        debug=args.debug,
        feeds=args.feeds,
        latitude=args.lat,
        longitude=args.lon,
    )

    # Import the Textual app lazily so --list / --help stay framework-free and fast.
    from buddy.app import BuddyApp

    BuddyApp(cfg).run()
    return 0
