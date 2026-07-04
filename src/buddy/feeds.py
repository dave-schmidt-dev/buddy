"""Background feed reactor for buddy's ambient reactivity seam.

This module is opt-in (INV-5): it imports stdlib network/threading modules at
module top, so it must NEVER be imported on the default run path.  It is wired
in lazily by events.get_reactor when a feed-enabled reactor is explicitly
requested.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
import urllib.request
from collections.abc import Callable

from buddy import config
from buddy.events import Event

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level HTTP helper (real network; callers inject a getter for tests)
# ---------------------------------------------------------------------------


def _get_json(url: str, user_agent: str, timeout: float) -> object:
    """Fetch *url* and return parsed JSON.

    Args:
        url: HTTP URL to fetch.
        user_agent: Value for the ``User-Agent`` request header.
        timeout: Socket timeout in seconds.

    Returns:
        Parsed JSON (dict, list, or scalar).
    """
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


# ---------------------------------------------------------------------------
# Pure fetchers — each takes an injected *getter* so tests need no network
# ---------------------------------------------------------------------------


def fetch_hn(
    getter: Callable[[str], object],
    count: int,
    seen_ids: set[int],
) -> list[Event]:
    """Fetch HN top stories and emit unseen headlines.

    Args:
        getter: Callable ``(url) -> parsed_json``; injected for testing.
        count: How many top-story IDs to consider.
        seen_ids: Mutable set of already-emitted story IDs (updated in-place).

    Returns:
        New ``feed.headline`` events (may be empty).
    """
    try:
        top_ids = getter("https://hacker-news.firebaseio.com/v0/topstories.json")
        events: list[Event] = []
        for story_id in top_ids[:count]:  # type: ignore[index]
            if story_id in seen_ids:
                continue
            item = getter(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            seen_ids.add(story_id)  # mark seen even if deleted/titleless, so we don't refetch it
            title = item.get("title") if isinstance(item, dict) else None  # type: ignore[union-attr]
            if title:
                events.append(Event("feed.headline", {"text": title, "id": story_id}))
        return events
    except Exception:
        logger.warning("fetch_hn failed", exc_info=True)
        return []


def fetch_weather(
    getter: Callable[[str], object],
    lat: float,
    lon: float,
    cache: dict,  # type: ignore[type-arg]
) -> list[Event]:
    """Fetch NWS hourly and 12h forecast and emit weather events.

    Args:
        getter: Callable ``(url) -> parsed_json``; injected for testing.
        lat: Latitude of the location.
        lon: Longitude of the location.
        cache: Mutable dict for caching inter-call state (``hourly_url``,
            ``forecast_url``).

    Returns:
        Subset of: weather.now, weather.wind, weather.humid, weather.comfort,
        weather.soon, weather.outlook — absent when source fields are missing.
        Degrades to ``[]`` on any outer error; outlook failure keeps the rest.
    """
    try:
        if cache.get("hourly_url") is None:
            points = getter(f"https://api.weather.gov/points/{lat},{lon}")
            cache["hourly_url"] = points["properties"]["forecastHourly"]  # type: ignore[index]
            cache["forecast_url"] = points["properties"]["forecast"]  # type: ignore[index]

        hourly = getter(cache["hourly_url"])
        periods = hourly["properties"]["periods"]  # type: ignore[index]
        p = periods[0]

        events: list[Event] = []

        # weather.now — always present
        events.append(
            Event("weather.now", {"text": f"{int(p['temperature'])}F {p['shortForecast']}"})
        )

        # weather.wind
        if p.get("windSpeed"):
            text = f"wind {p.get('windDirection', '')} {p['windSpeed']}".strip()
            events.append(Event("weather.wind", {"text": text}))

        # weather.humid
        rh = p.get("relativeHumidity", {}).get("value")
        if rh is not None:
            events.append(Event("weather.humid", {"text": f"humidity {rh}%"}))

        # weather.comfort (dewpoint-based feel)
        dp_raw = p.get("dewpoint", {}).get("value")
        if dp_raw is not None:
            dp_f = dp_raw * 9 / 5 + 32
            if dp_f >= 70:
                comfort_text: str | None = "muggy out"
            elif dp_f >= 60:
                comfort_text = "a little humid"
            elif dp_f <= 40:
                comfort_text = "crisp + dry"
            else:
                comfort_text = None
            if comfort_text is not None:
                events.append(Event("weather.comfort", {"text": comfort_text}))

        # weather.soon — scan next 5h for rising precip
        p0_precip = p.get("probabilityOfPrecipitation", {}).get("value") or 0
        if p0_precip < 50:
            for i, period in enumerate(periods[1:6], start=1):
                precip = period.get("probabilityOfPrecipitation", {}).get("value") or 0
                if precip >= 50:
                    events.append(Event("weather.soon", {"text": f"rain likely ~{i}h"}))
                    break

        # weather.outlook — from 12h /forecast; nested so a failure keeps the hourly batch
        try:
            forecast = getter(cache["forecast_url"])
            fp = forecast["properties"]["periods"][0]  # type: ignore[index]
            if fp.get("isDaytime") and fp.get("temperature") is not None:
                events.append(
                    Event(
                        "weather.outlook",
                        {"text": f"high near {int(fp['temperature'])}F"},
                    )
                )
            elif fp.get("name") and fp.get("shortForecast"):
                events.append(
                    Event(
                        "weather.outlook",
                        {"text": f"{fp['name']}: {fp['shortForecast']}"},
                    )
                )
        except Exception:
            logger.warning("fetch_weather outlook failed", exc_info=True)

        return events
    except Exception:
        logger.warning("fetch_weather failed", exc_info=True)
        return []


def fetch_alerts(
    getter: Callable[[str], object],
    lat: float,
    lon: float,
) -> list[Event]:
    """Fetch NWS active weather alerts.

    Args:
        getter: Callable ``(url) -> parsed_json``; injected for testing.
        lat: Latitude.
        lon: Longitude.

    Returns:
        ``nws.alert`` events for each active alert (may be empty).
    """
    try:
        data = getter(f"https://api.weather.gov/alerts/active?point={lat},{lon}")
        events: list[Event] = []
        for feature in data.get("features", []):  # type: ignore[union-attr]
            props = feature.get("properties", {})
            text = props.get("event", "")
            if text:
                events.append(
                    Event(
                        "nws.alert",
                        {
                            "text": text,
                            "severity": props.get("severity"),
                            "id": props.get("id")
                            or feature.get("id")
                            or f"{text}|{props.get('severity')}",
                        },
                    )
                )
        return events
    except Exception:
        logger.warning("fetch_alerts failed", exc_info=True)
        return []


# ---------------------------------------------------------------------------
# FeedReactor — background thread drains into a queue; poll() is non-blocking
# ---------------------------------------------------------------------------


class FeedReactor:
    """Opt-in reactor that fetches real-world content on a background thread.

    Implements the ``Reactor`` protocol: the app calls ``poll()`` each tick to
    drain queued events without blocking the render loop.

    Args:
        feeds: Tuple subset of ``{"hn", "weather", "nws"}`` enabling each feed.
        latitude: Latitude for weather/NWS feeds.
        longitude: Longitude for weather/NWS feeds.
        user_agent: HTTP ``User-Agent`` string (must be non-empty for NWS).
        getter: Injectable HTTP getter for testing; defaults to ``_get_json``.
    """

    def __init__(
        self,
        feeds: tuple[str, ...],
        latitude: float | None = None,
        longitude: float | None = None,
        user_agent: str = config.FEED_USER_AGENT,
        getter: Callable[[str], object] | None = None,
    ) -> None:
        self._feeds = feeds
        self._lat = latitude
        self._lon = longitude
        if getter is None:
            _ua = user_agent
            self._getter: Callable[[str], object] = lambda url: _get_json(
                url, _ua, config.FEED_HTTP_TIMEOUT_S
            )
        else:
            self._getter = getter
        self._queue: queue.Queue[Event] = queue.Queue()
        self._stop = threading.Event()
        self._seen_ids: set[int] = set()
        self._cache: dict = {}  # type: ignore[type-arg]
        if ("weather" in feeds or "nws" in feeds) and (latitude is None or longitude is None):
            raise ValueError("weather/nws feeds require latitude and longitude")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        """Background worker: poll feeds on schedule, put events on queue."""
        now = time.monotonic()
        next_due: dict[str, float] = {feed: now for feed in self._feeds}
        intervals: dict[str, float] = {
            "hn": config.FEED_HN_INTERVAL_S,
            "weather": config.FEED_WEATHER_INTERVAL_S,
            "nws": config.FEED_ALERT_INTERVAL_S,
        }

        while not self._stop.is_set():
            now = time.monotonic()
            for feed_name in list(next_due):
                if now >= next_due[feed_name]:
                    try:
                        if feed_name == "hn":
                            evts = fetch_hn(self._getter, config.FEED_HN_COUNT, self._seen_ids)
                        elif feed_name == "weather":
                            evts = fetch_weather(self._getter, self._lat, self._lon, self._cache)
                        else:  # "nws"
                            evts = fetch_alerts(self._getter, self._lat, self._lon)
                        for evt in evts:
                            self._queue.put(evt)
                    except Exception:
                        logger.warning("FeedReactor worker error for %s", feed_name, exc_info=True)
                    next_due[feed_name] = time.monotonic() + intervals[feed_name]
            self._stop.wait(1.0)

    def poll(self) -> list[Event]:
        """Drain the event queue without blocking.

        Returns:
            All events accumulated since the last poll (may be empty).
        """
        events: list[Event] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events

    def close(self) -> None:
        """Signal the background thread to stop and wait for it to exit."""
        self._stop.set()
        self._thread.join(timeout=config.FEED_HTTP_TIMEOUT_S + 1)
