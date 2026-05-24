"""Weather service - fetches real-time weather from data.gov.my."""

import requests
from typing import Optional
from app.config import settings


class WeatherService:
    """Handles data.gov.my Weather API interactions."""

    @staticmethod
    def fetch_current_weather(state: Optional[str] = None) -> dict:
        """
        Fetch current weather conditions from data.gov.my.
        
        Returns weather data with condition, temperature, humidity.
        Falls back to simulated data if API is unavailable.
        """
        try:
            resp = requests.get(settings.WEATHER_BASE_URL, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return WeatherService._parse_weather_response(data)
                return data
        except (requests.RequestException, ValueError) as e:
            return WeatherService._fallback_weather()

        return WeatherService._fallback_weather()

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
