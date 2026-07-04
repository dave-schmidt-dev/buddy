"""Tests for buddy.feeds — opt-in background feed reactor.

All tests use an injected fake getter; no real network calls are made.
"""

from __future__ import annotations

import urllib.error
from collections.abc import Callable

import pytest

from buddy.events import Event
from buddy.feeds import FeedReactor, fetch_alerts, fetch_hn, fetch_weather

# ---------------------------------------------------------------------------
# Shared test constants
# ---------------------------------------------------------------------------

_LAT = 38.9
_LON = -77.0
_HOURLY_URL = "https://api.weather.gov/gridpoints/TEST/0,0/forecast/hourly"
_FORECAST_URL = "https://api.weather.gov/gridpoints/TEST/0,0/forecast"


# ---------------------------------------------------------------------------
# Getter factory helpers
# ---------------------------------------------------------------------------


def _exact_getter(table: dict[str, object]) -> Callable[[str], object]:
    """Return a getter backed by exact-URL key lookup."""

    def getter(url: str) -> object:
        return table[url]

    return getter


def _raising_getter(exc: Exception) -> Callable[[str], object]:
    """Return a getter that always raises *exc*."""

    def getter(url: str) -> object:
        raise exc

    return getter


def _make_period(temp: int, forecast: str, precip: int | None = 0) -> dict:  # type: ignore[type-arg]
    return {
        "temperature": temp,
        "temperatureUnit": "F",
        "shortForecast": forecast,
        "probabilityOfPrecipitation": {"value": precip},
    }


def _make_dispatch_getter(
    hourly_periods: list,  # type: ignore[type-arg]
    forecast_periods: list | None = None,  # type: ignore[type-arg]
    *,
    raise_for_forecast: bool = False,
) -> Callable[[str], object]:
    """Dispatch getter for weather tests; routes by URL substring.

    Routes:
        ``/points/``      -> points response with both cached URLs.
        ``hourly`` in url -> hourly forecast with *hourly_periods*.
        ``/forecast``     -> 12h forecast with *forecast_periods*, or raises
                             ``ValueError`` when *raise_for_forecast* is True.
    """

    def getter(url: str) -> object:
        if "/points/" in url:
            return {
                "properties": {
                    "forecastHourly": _HOURLY_URL,
                    "forecast": _FORECAST_URL,
                }
            }
        if "hourly" in url:
            return {"properties": {"periods": hourly_periods}}
        if "/forecast" in url:
            if raise_for_forecast:
                raise ValueError("forecast network error")
            if forecast_periods is None:
                raise KeyError(url)
            return {"properties": {"periods": forecast_periods}}
        raise KeyError(url)

    return getter


# ---------------------------------------------------------------------------
# HN tests
# ---------------------------------------------------------------------------


def test_hn_fetch_returns_headline_events() -> None:
    """Getter with two stories -> two feed.headline events with correct text/id."""
    getter = _exact_getter(
        {
            "https://hacker-news.firebaseio.com/v0/topstories.json": [1, 2],
            "https://hacker-news.firebaseio.com/v0/item/1.json": {
                "id": 1,
                "type": "story",
                "title": "Alpha Story",
                "by": "user1",
                "score": 100,
            },
            "https://hacker-news.firebaseio.com/v0/item/2.json": {
                "id": 2,
                "type": "story",
                "title": "Beta Story",
                "by": "user2",
                "score": 50,
            },
        }
    )
    seen: set[int] = set()
    events = fetch_hn(getter, 2, seen)
    assert len(events) == 2
    assert all(e.kind == "feed.headline" for e in events)
    assert events[0].data == {"text": "Alpha Story", "id": 1}
    assert events[1].data == {"text": "Beta Story", "id": 2}


def test_hn_dedup_skips_seen_ids() -> None:
    """Calling fetch_hn twice with the same seen_ids set yields events only the first time."""
    getter = _exact_getter(
        {
            "https://hacker-news.firebaseio.com/v0/topstories.json": [1, 2],
            "https://hacker-news.firebaseio.com/v0/item/1.json": {"id": 1, "title": "Alpha"},
            "https://hacker-news.firebaseio.com/v0/item/2.json": {"id": 2, "title": "Beta"},
        }
    )
    seen: set[int] = set()
    first = fetch_hn(getter, 2, seen)
    assert len(first) == 2
    second = fetch_hn(getter, 2, seen)
    assert second == []


# ---------------------------------------------------------------------------
# Weather tests
# ---------------------------------------------------------------------------


def test_weather_builds_now_event() -> None:
    """Canned points+hourly response -> weather.now event with text '72F Sunny'."""
    periods = [
        _make_period(72, "Sunny", 10),
        _make_period(70, "Partly Cloudy", 20),
    ]
    getter = _exact_getter(
        {
            f"https://api.weather.gov/points/{_LAT},{_LON}": {
                "properties": {
                    "forecastHourly": _HOURLY_URL,
                    "forecast": _FORECAST_URL,
                }
            },
            _HOURLY_URL: {"properties": {"periods": periods}},
            # _FORECAST_URL absent -> nested try/except drops outlook silently
        }
    )
    events = fetch_weather(getter, _LAT, _LON, {})
    now = next((e for e in events if e.kind == "weather.now"), None)
    assert now is not None
    assert now.data["text"] == "72F Sunny"  # type: ignore[index]


def test_weather_soon_when_precip_rises() -> None:
    """weather.soon emitted when precip rises in the scan window; absent when it doesn't."""
    # Case 1: period at index i=2 (hours ahead) crosses the 50% threshold
    periods_rise = [
        _make_period(72, "Sunny", 10),  # p0: precip < 50 -> scan begins
        _make_period(70, "Cloudy", 20),  # i=1: still below threshold
        _make_period(68, "Rainy", 60),  # i=2: precip >= 50 -> emit weather.soon
        _make_period(66, "Rainy", 80),  # i=3..5: not reached
        _make_period(65, "Rainy", 90),
        _make_period(64, "Rainy", 90),
    ]
    getter_rise = _exact_getter(
        {
            f"https://api.weather.gov/points/{_LAT},{_LON}": {
                "properties": {
                    "forecastHourly": _HOURLY_URL,
                    "forecast": _FORECAST_URL,
                }
            },
            _HOURLY_URL: {"properties": {"periods": periods_rise}},
            # _FORECAST_URL absent -> nested try/except drops outlook silently
        }
    )
    events_rise = fetch_weather(getter_rise, _LAT, _LON, {})
    soon = next((e for e in events_rise if e.kind == "weather.soon"), None)
    assert soon is not None
    assert soon.data["text"] == "rain likely ~2h"  # type: ignore[index]

    # Case 2: no precip crosses 50% -> no weather.soon event
    periods_dry = [_make_period(72 - i, "Clear", 5) for i in range(6)]
    getter_dry = _exact_getter(
        {
            f"https://api.weather.gov/points/{_LAT},{_LON}": {
                "properties": {
                    "forecastHourly": _HOURLY_URL,
                    "forecast": _FORECAST_URL,
                }
            },
            _HOURLY_URL: {"properties": {"periods": periods_dry}},
            # _FORECAST_URL absent -> nested try/except drops outlook silently
        }
    )
    events_dry = fetch_weather(getter_dry, _LAT, _LON, {})
    assert not any(e.kind == "weather.soon" for e in events_dry)


def test_weather_now_and_extras() -> None:
    """Rich hourly period -> weather.now, wind, humid, and comfort all emitted."""
    hourly_period = {
        "temperature": 91,
        "temperatureUnit": "F",
        "shortForecast": "Sunny",
        "windDirection": "NW",
        "windSpeed": "5 mph",
        "relativeHumidity": {"value": 56},
        "dewpoint": {"value": 22.7},  # 22.7 C -> 72.86 F -> "muggy out"
        "probabilityOfPrecipitation": {"value": 1},
        "isDaytime": True,
    }
    getter = _make_dispatch_getter(hourly_periods=[hourly_period])
    events = fetch_weather(getter, _LAT, _LON, {})
    kinds = {e.kind: e for e in events}

    assert "weather.now" in kinds
    assert kinds["weather.now"].data["text"] == "91F Sunny"  # type: ignore[index]

    assert "weather.wind" in kinds
    assert kinds["weather.wind"].data["text"] == "wind NW 5 mph"  # type: ignore[index]

    assert "weather.humid" in kinds
    assert kinds["weather.humid"].data["text"] == "humidity 56%"  # type: ignore[index]

    assert "weather.comfort" in kinds
    assert kinds["weather.comfort"].data["text"] == "muggy out"  # type: ignore[index]


def test_weather_outlook_high() -> None:
    """12h forecast isDaytime period -> weather.outlook 'high near 98F'."""
    hourly_period = _make_period(85, "Partly Cloudy", 5)
    forecast_period = {
        "name": "Independence Day",
        "isDaytime": True,
        "temperature": 98,
        "shortForecast": "Mostly Sunny",
    }
    getter = _make_dispatch_getter(
        hourly_periods=[hourly_period],
        forecast_periods=[forecast_period],
    )
    events = fetch_weather(getter, _LAT, _LON, {})
    outlook = next((e for e in events if e.kind == "weather.outlook"), None)
    assert outlook is not None
    assert outlook.data["text"] == "high near 98F"  # type: ignore[index]


def test_weather_outlook_failure_keeps_hourly() -> None:
    """Forecast fetch failure -> weather.now still returned; outlook silently dropped."""
    hourly_period = _make_period(78, "Clear", 0)
    getter = _make_dispatch_getter(
        hourly_periods=[hourly_period],
        raise_for_forecast=True,
    )
    events = fetch_weather(getter, _LAT, _LON, {})
    now = next((e for e in events if e.kind == "weather.now"), None)
    assert now is not None
    assert not any(e.kind == "weather.outlook" for e in events)


# ---------------------------------------------------------------------------
# Alerts tests
# ---------------------------------------------------------------------------


def test_alerts_map_severity_and_id() -> None:
    """Alert feature -> nws.alert event with correct severity and id fields."""
    alert_id = "urn:oid:2.49.0.1.840.0.abc123"
    getter = _exact_getter(
        {
            f"https://api.weather.gov/alerts/active?point={_LAT},{_LON}": {
                "features": [
                    {
                        "id": alert_id,
                        "properties": {
                            "id": alert_id,
                            "event": "Tornado Warning",
                            "severity": "Severe",
                        },
                    }
                ]
            }
        }
    )
    events = fetch_alerts(getter, _LAT, _LON)
    assert len(events) == 1
    evt = events[0]
    assert evt.kind == "nws.alert"
    assert evt.data["text"] == "Tornado Warning"  # type: ignore[index]
    assert evt.data["severity"] == "Severe"  # type: ignore[index]
    assert evt.data["id"] == alert_id  # type: ignore[index]


# ---------------------------------------------------------------------------
# Failure / degradation tests
# ---------------------------------------------------------------------------


def test_fetch_failure_degrades_to_empty() -> None:
    """A getter that raises URLError -> each fetcher returns [] without raising."""
    bad = _raising_getter(urllib.error.URLError("boom"))

    assert fetch_hn(bad, 8, set()) == []
    assert fetch_weather(bad, _LAT, _LON, {}) == []
    assert fetch_alerts(bad, _LAT, _LON) == []


# ---------------------------------------------------------------------------
# Reactor drain tests
# ---------------------------------------------------------------------------


def test_reactor_poll_drains_then_empty() -> None:
    """poll() drains the internal queue deterministically; second call returns []."""
    # feeds=() means the worker thread never produces its own events.
    reactor = FeedReactor(feeds=(), getter=_raising_getter(ValueError("unused")))
    try:
        sentinel = [
            Event("test.a", {"x": 1}),
            Event("test.b", {"x": 2}),
        ]
        for evt in sentinel:
            reactor._queue.put(evt)

        drained = reactor.poll()
        assert drained == sentinel

        assert reactor.poll() == []
    finally:
        reactor.close()


# ---------------------------------------------------------------------------
# New tests for the four review fixes
# ---------------------------------------------------------------------------


def test_hn_marks_deleted_item_seen() -> None:
    """Deleted/titleless item is added to seen_ids so it is never refetched."""
    call_counts: dict[str, int] = {"item_1": 0}

    def counting_getter(url: str) -> object:
        if url == "https://hacker-news.firebaseio.com/v0/topstories.json":
            return [1]
        if url == "https://hacker-news.firebaseio.com/v0/item/1.json":
            call_counts["item_1"] += 1
            return {"deleted": True}
        raise KeyError(url)

    seen: set[int] = set()
    events = fetch_hn(counting_getter, 5, seen)
    assert events == []
    assert 1 in seen  # marked even though no title was emitted

    # Second call with the same seen_ids must skip item 1 entirely.
    events2 = fetch_hn(counting_getter, 5, seen)
    assert events2 == []
    assert call_counts["item_1"] == 1  # item fetched exactly once across both calls


def test_alerts_uses_composite_id_when_missing() -> None:
    """Composite fallback id is used when both props.id and feature.id are absent."""
    event_name = "Wind Advisory"
    severity = "Moderate"
    getter = _exact_getter(
        {
            f"https://api.weather.gov/alerts/active?point={_LAT},{_LON}": {
                "features": [
                    {
                        # no feature-level id key
                        "properties": {
                            "event": event_name,
                            "severity": severity,
                            # no properties-level id key
                        },
                    }
                ]
            }
        }
    )
    events = fetch_alerts(getter, _LAT, _LON)
    assert len(events) == 1
    assert events[0].data["id"] == f"{event_name}|{severity}"  # type: ignore[index]


def test_reactor_requires_latlon_for_weather() -> None:
    """FeedReactor raises ValueError for weather/nws feeds without lat/lon."""
    dummy_getter = _raising_getter(ValueError("no network"))

    with pytest.raises(ValueError, match="latitude and longitude"):
        FeedReactor(("weather",), getter=dummy_getter)

    with pytest.raises(ValueError, match="latitude and longitude"):
        FeedReactor(("nws",), getter=dummy_getter)

    # "hn" feed must not raise even without lat/lon
    reactor = FeedReactor(("hn",), getter=dummy_getter)
    reactor.close()
