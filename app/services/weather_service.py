"""Weather service - fetches real-time weather from data.gov.my."""

import requests
import time
from typing import Optional
from app.config import settings

# Module-level cache — avoids redundant external API calls
_weather_cache: Optional[dict] = None
_weather_cache_time: float = 0
CACHE_TTL = 60  # seconds


class WeatherService:
    """Handles data.gov.my Weather API interactions."""

    @staticmethod
    def fetch_current_weather(state: Optional[str] = None) -> dict:
        """
        Fetch current weather conditions from data.gov.my.
        
        Returns weather data with condition, temperature, humidity.
        Falls back to simulated data if API is unavailable.
        Results are cached for 60 seconds to avoid redundant API calls.
        """
        global _weather_cache, _weather_cache_time

        # Return cached data if still fresh
        if _weather_cache and (time.time() - _weather_cache_time) < CACHE_TTL:
            return _weather_cache

        try:
            start = time.time()
            resp = requests.get(settings.WEATHER_BASE_URL, timeout=10)
            elapsed_ms = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    _weather_cache = WeatherService._parse_weather_response(data)
                    _weather_cache_time = time.time()
                    from app.database import log_api_call
                    log_api_call("weather", settings.WEATHER_BASE_URL, "success", elapsed_ms)
                    return _weather_cache
                _weather_cache = data
                _weather_cache_time = time.time()
                from app.database import log_api_call
                log_api_call("weather", settings.WEATHER_BASE_URL, "success", elapsed_ms)
                return data
            else:
                from app.database import log_api_call
                log_api_call("weather", settings.WEATHER_BASE_URL, f"http_{resp.status_code}", elapsed_ms)
        except (requests.RequestException, ValueError) as e:
            from app.database import log_api_call
            log_api_call("weather", settings.WEATHER_BASE_URL, "error", 0)

        # Use cached data even if stale as fallback
        if _weather_cache:
            return _weather_cache

        fallback = WeatherService._fallback_weather()
        _weather_cache = fallback
        _weather_cache_time = time.time()
        return fallback

    @staticmethod
    def _parse_weather_response(data: list) -> dict:
        """Parse weather API response into a clean format."""
        if not data:
            return WeatherService._fallback_weather()

        # Take first station's data
        station = data[0] if isinstance(data, list) else data
        return {
            "condition": station.get("weather", station.get("condition", "Clear")),
            "temperature": station.get("temp", station.get("temperature", 28.0)),
            "humidity": station.get("humidity", 70),
            "station": station.get("station", station.get("name", "Kuala Lumpur")),
            "source": "data.gov.my",
        }

    @staticmethod
    def _fallback_weather() -> dict:
        """Return reasonable default weather when API is unavailable."""
        return {
            "condition": "Clear",
            "temperature": 28.0,
            "humidity": 70,
            "station": "Kuala Lumpur (fallback)",
            "source": "fallback",
        }
