"""Tests for buddy.cli — argument parsing and main() behavior."""

from __future__ import annotations

import pytest

from buddy.cli import build_parser, main


class TestSpeedValidation:
    """Speed argument edge cases."""

    def test_speed_zero_rejected(self):
        """Zero is outside (0, 10] so the parser must raise SystemExit."""
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--speed", "0"])

    def test_speed_negative_rejected(self):
        """Negative speed is invalid."""
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--speed", "-1"])

    def test_speed_nonnumeric_rejected(self):
        """Non-numeric string is invalid."""
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--speed", "abc"])

    def test_speed_valid_accepted(self):
        """A valid speed in range parses correctly."""
        args = build_parser().parse_args(["--speed", "2.5"])
        assert args.speed == pytest.approx(2.5)

    def test_speed_upper_bound_rejected(self):
        """Speed above SPEED_MAX is invalid."""
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--speed", "999"])


class TestAnimalValidation:
    """--animal must be enforced by the parser (clean error, not a traceback)."""

    def test_unknown_animal_rejected(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--animal", "dragon"])

    def test_known_animal_accepted(self):
        assert build_parser().parse_args(["--animal", "capybara"]).animal == "capybara"

    def test_random_accepted(self):
        assert build_parser().parse_args(["--animal", "random"]).animal == "random"


class TestMain:
    """Behaviour of main()."""

    def test_list_returns_zero(self):
        """--list exits with code 0."""
        assert main(["--list"]) == 0

    def test_main_launches_app_with_correct_config(self, monkeypatch):
        """main() builds a BuddyApp from CLI args and calls .run(); returns 0."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--animal", "cat", "--seed", "1"])

        assert result == 0
        assert len(launched) == 1
        cfg = launched[0]
        assert cfg.animal == "cat"
        assert cfg.seed == 1


class TestFeedsValidation:
    """--feeds argument parsing and geo-guard validation."""

    def test_feeds_parses_to_tuple(self):
        """--feeds hn,weather produces a tuple of the two tokens."""
        args = build_parser().parse_args(["--feeds", "hn,weather"])
        assert args.feeds == ("hn", "weather")

    def test_bad_feed_token_rejected(self):
        """An unknown feed token causes the parser to raise SystemExit."""
        with pytest.raises(SystemExit):
            build_parser().parse_args(["--feeds", "hn,bogus"])

    def test_weather_feed_without_location_rejected(self):
        """--feeds weather without --lat/--lon triggers parser.error (SystemExit)."""
        with pytest.raises(SystemExit):
            main(["--feeds", "weather"])

    def test_nws_feed_without_location_rejected(self):
        """--feeds nws without --lat/--lon triggers parser.error (SystemExit)."""
        with pytest.raises(SystemExit):
            main(["--feeds", "nws"])

    def test_feed_latlon_plumb_into_config(self, monkeypatch):
        """Feeds and lat/lon are forwarded into the BuddyConfig passed to BuddyApp."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--feeds", "weather", "--lat", "38.9", "--lon", "-77.0"])

        assert result == 0
        assert len(launched) == 1
        cfg = launched[0]
        assert cfg.feeds == ("weather",)
        assert cfg.latitude == pytest.approx(38.9)
        assert cfg.longitude == pytest.approx(-77.0)

    def test_zip_resolves_to_latlon(self, monkeypatch):
        """--zip geocodes to lat/lon via the resolver and plumbs into BuddyConfig."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setattr("buddy.cli._resolve_zip", lambda z: (38.9, -77.0))

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--feeds", "weather", "--zip", "20500"])

        assert result == 0
        assert len(launched) == 1
        cfg = launched[0]
        assert cfg.feeds == ("weather",)
        assert cfg.latitude == pytest.approx(38.9)
        assert cfg.longitude == pytest.approx(-77.0)

    def test_zip_failure_is_clean_error(self, monkeypatch):
        """A resolver failure becomes a clean SystemExit (parser.error path), no traceback."""
        monkeypatch.setattr(
            "buddy.cli._resolve_zip", lambda z: (_ for _ in ()).throw(ValueError("boom"))
        )

        with pytest.raises(SystemExit):
            main(["--feeds", "weather", "--zip", "00000"])

    def test_explicit_latlon_skips_zip_resolution(self, monkeypatch):
        """When --lat and --lon are already supplied, --zip resolver is never called."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        def resolver_must_not_be_called(z):
            raise AssertionError("_resolve_zip called despite explicit lat/lon")

        monkeypatch.setattr("buddy.cli._resolve_zip", resolver_must_not_be_called)

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--feeds", "weather", "--lat", "1.0", "--lon", "2.0", "--zip", "20500"])

        assert result == 0
        assert len(launched) == 1
        cfg = launched[0]
        assert cfg.latitude == pytest.approx(1.0)
        assert cfg.longitude == pytest.approx(2.0)
