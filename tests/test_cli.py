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
