"""Weather agent — answers weather-related queries."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherAgent(BaseAgent):
    """Fetches weather data and answers questions about current conditions.

    Uses the Open-Meteo public API (no key required) by default.  Set
    ``WEATHER_API_KEY`` and ``WEATHER_API_URL`` in the environment to swap in
    a different provider.
    """

    name: str = "weather"
    keywords: List[str] = ["weather", "temperature", "forecast", "rain", "sunny", "cloudy"]

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        self._api_url = api_url or os.getenv("WEATHER_API_URL", _OPEN_METEO_URL)
        self._api_key = api_key or os.getenv("WEATHER_API_KEY", "")
        self._timeout = timeout

    def process(self, content: str, session_id: str) -> str:
        logger.info("WeatherAgent handling session=%s", session_id)
        location = self._extract_location(content)
        try:
            data = self._fetch_weather(location)
            return self._format_weather(data, location)
        except Exception as exc:
            logger.error("WeatherAgent fetch error: %s", exc)
            return f"Sorry, I couldn't retrieve weather data for '{location}' right now."

    # ── Private helpers ────────────────────────────────────────────────────

    def _extract_location(self, content: str) -> str:
        """Very simple keyword extraction — override for NLP-powered parsing."""
        lower = content.lower()
        for keyword in ("in ", "for ", "at "):
            idx = lower.find(keyword)
            if idx != -1:
                return content[idx + len(keyword):].strip().rstrip("?!.")
        return "New York"

    def _fetch_weather(self, location: str) -> Dict[str, Any]:
        """Fetch current weather from Open-Meteo (no auth required)."""
        # Geocode to lat/lon using Open-Meteo's geocoding endpoint
        geo_resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1},
            timeout=self._timeout,
        )
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        results = geo_data.get("results", [])
        if not results:
            raise ValueError(f"Location not found: {location}")
        lat = results[0]["latitude"]
        lon = results[0]["longitude"]

        wx_resp = requests.get(
            self._api_url,
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
            },
            timeout=self._timeout,
        )
        wx_resp.raise_for_status()
        return wx_resp.json()

    @staticmethod
    def _format_weather(data: Dict[str, Any], location: str) -> str:
        cw = data.get("current_weather", {})
        temp = cw.get("temperature", "?")
        wind = cw.get("windspeed", "?")
        code = cw.get("weathercode", "?")
        return (
            f"Current weather in {location}: "
            f"{temp}°C, wind {wind} km/h (WMO code {code})."
        )
