"""Tests for buddy.cli — argument parsing and main() behavior."""

from __future__ import annotations

import os

import pytest

from buddy.cli import _load_dotenv, build_parser, main


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
        assert build_parser().parse_args(["--animal", "possum"]).animal == "possum"

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

    def test_weather_feed_without_location_degrades(self, monkeypatch):
        """--feeds weather without location drops weather and returns 0, no SystemExit."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setattr("buddy.cli._load_dotenv", lambda path=None: None)
        monkeypatch.delenv("BUDDY_ZIP", raising=False)
        monkeypatch.delenv("BUDDY_LAT", raising=False)
        monkeypatch.delenv("BUDDY_LON", raising=False)

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--feeds", "weather"])
        assert result == 0
        assert len(launched) == 1
        assert launched[0].feeds == ()

    def test_nws_feed_without_location_degrades(self, monkeypatch):
        """--feeds nws without location drops nws and returns 0, no SystemExit."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setattr("buddy.cli._load_dotenv", lambda path=None: None)
        monkeypatch.delenv("BUDDY_ZIP", raising=False)
        monkeypatch.delenv("BUDDY_LAT", raising=False)
        monkeypatch.delenv("BUDDY_LON", raising=False)

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--feeds", "nws"])
        assert result == 0
        assert len(launched) == 1
        assert launched[0].feeds == ()

    def test_feed_latlon_plumb_into_config(self, monkeypatch):
        """Feeds and lat/lon are forwarded into the BuddyConfig passed to BuddyApp."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setattr("buddy.cli._load_dotenv", lambda path=None: None)

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

        monkeypatch.setattr("buddy.cli._load_dotenv", lambda path=None: None)
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

    def test_zip_failure_degrades(self, monkeypatch):
        """A resolver failure drops weather feed and returns 0, no SystemExit."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setattr("buddy.cli._load_dotenv", lambda path=None: None)
        monkeypatch.setattr(
            "buddy.cli._resolve_zip", lambda z: (_ for _ in ()).throw(ValueError("boom"))
        )

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--feeds", "weather", "--zip", "00000"])
        assert result == 0
        assert len(launched) == 1
        assert launched[0].feeds == ()

    def test_explicit_latlon_skips_zip_resolution(self, monkeypatch):
        """When --lat and --lon are already supplied, --zip resolver is never called."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setattr("buddy.cli._load_dotenv", lambda path=None: None)

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

    def test_all_feeds_without_location_keeps_hn(self, monkeypatch):
        """With hn,weather,nws but no location, hn is kept and weather+nws are dropped."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setattr("buddy.cli._load_dotenv", lambda path=None: None)
        monkeypatch.delenv("BUDDY_ZIP", raising=False)
        monkeypatch.delenv("BUDDY_LAT", raising=False)
        monkeypatch.delenv("BUDDY_LON", raising=False)

        def resolver_must_not_be_called(z):
            raise AssertionError("_resolve_zip should not be called when no zip is provided")

        monkeypatch.setattr("buddy.cli._resolve_zip", resolver_must_not_be_called)

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--feeds", "hn,weather,nws"])
        assert result == 0
        assert len(launched) == 1
        assert launched[0].feeds == ("hn",)

    def test_malformed_env_latlon_degrades(self, monkeypatch):
        """BUDDY_LAT/BUDDY_LON with non-numeric values degrade (no ValueError traceback)."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setattr("buddy.cli._load_dotenv", lambda *a, **k: None)
        monkeypatch.setenv("BUDDY_LAT", "not-a-number")
        monkeypatch.setenv("BUDDY_LON", "also-bad")
        monkeypatch.delenv("BUDDY_ZIP", raising=False)

        def resolver_must_not_be_called(z):
            raise AssertionError("_resolve_zip should not be reached when no zip is set")

        monkeypatch.setattr("buddy.cli._resolve_zip", resolver_must_not_be_called)

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--feeds", "weather"])
        assert result == 0
        assert len(launched) == 1
        assert launched[0].feeds == ()


class TestDotenv:
    """.env loading and INV-5 gating."""

    def test_load_dotenv_populates_env(self, monkeypatch, tmp_path):
        """_load_dotenv sets env vars from file (skips comments and blank lines)."""
        monkeypatch.delenv("BUDDY_ZIP", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\nBUDDY_ZIP=20169\n\n")
        _load_dotenv(env_file)
        assert os.environ["BUDDY_ZIP"] == "20169"

    def test_load_dotenv_does_not_override_existing(self, monkeypatch, tmp_path):
        """_load_dotenv respects existing env vars (setdefault semantics)."""
        monkeypatch.setenv("BUDDY_ZIP", "99999")
        env_file = tmp_path / ".env"
        env_file.write_text("BUDDY_ZIP=20169\n")
        _load_dotenv(env_file)
        assert os.environ["BUDDY_ZIP"] == "99999"

    def test_env_zip_used_for_weather_feed(self, monkeypatch):
        """BUDDY_ZIP in env is geocoded and forwarded to BuddyConfig when weather requested."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setenv("BUDDY_ZIP", "20169")
        monkeypatch.setattr("buddy.cli._load_dotenv", lambda path=None: None)
        monkeypatch.setattr("buddy.cli._resolve_zip", lambda z: (38.9, -77.6))

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--feeds", "weather"])

        assert result == 0
        assert len(launched) == 1
        cfg = launched[0]
        assert cfg.latitude == pytest.approx(38.9)
        assert cfg.longitude == pytest.approx(-77.6)

    def test_default_run_ignores_env_and_does_not_geocode(self, monkeypatch):
        """INV-5: default run (no weather/nws) never reads .env or geocodes."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setenv("BUDDY_ZIP", "20169")

        def resolver_must_not_be_called(z):
            raise AssertionError("_resolve_zip called on default run")

        monkeypatch.setattr("buddy.cli._resolve_zip", resolver_must_not_be_called)

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main([])

        assert result == 0

    def test_cli_latlon_overrides_env_zip(self, monkeypatch):
        """Explicit --lat/--lon wins over BUDDY_ZIP in env; resolver never called."""
        from buddy.app import BuddyApp
        from buddy.config import BuddyConfig

        monkeypatch.setenv("BUDDY_ZIP", "20169")
        monkeypatch.setattr("buddy.cli._load_dotenv", lambda path=None: None)

        def resolver_must_not_be_called(z):
            raise AssertionError("_resolve_zip called despite explicit lat/lon")

        monkeypatch.setattr("buddy.cli._resolve_zip", resolver_must_not_be_called)

        launched: list[BuddyConfig] = []

        def fake_init(self, cfg=None):
            launched.append(cfg)

        monkeypatch.setattr(BuddyApp, "__init__", fake_init)
        monkeypatch.setattr(BuddyApp, "run", lambda self, **kw: None)

        result = main(["--feeds", "weather", "--lat", "1.0", "--lon", "2.0"])

        assert result == 0
        assert len(launched) == 1
        cfg = launched[0]
        assert cfg.latitude == pytest.approx(1.0)
        assert cfg.longitude == pytest.approx(2.0)
