"""AI prediction service - integrates with Google AI Studio (Gemini API)."""

import re
from datetime import datetime
from typing import Optional
from app.config import settings


class AIPredictionService:
    """
    Core AI integration layer.
    Builds structured prompts with transit/weather context and sends them
    to the Gemini API for crowd level classification.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._model = None

    def _get_model(self):
        """Lazy-load the Gemini model."""
        if self._model is None and self.api_key:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)
        return self._model

    def build_prompt(self, time: str, day: str, weather_condition: str,
                     temperature: float, route_name: str, route_id: str) -> str:
        """
        Build a structured prompt for the Gemini API.
        The prompt asks the AI to classify crowd level based on contextual variables.
        """
        prompt = f"""You are TransitSight, a smart public transport crowd predictor for Malaysia.
Your task is to predict the crowd level for a transit route based on the following context.

Context:
- Route: {route_name} ({route_id})
- Time: {time}
- Day: {day}
- Weather: {weather_condition}
- Temperature: {temperature}°C

Based on your knowledge of typical crowd patterns in Malaysian public transit,
classify the expected crowd level as exactly one of: Low, Medium, or Full.

Consider these factors:
- Peak hours (7-9 AM, 5-7 PM weekdays) tend to be Medium to Full
- Midday and late evening tend to be Low to Medium
- Rainy weather often increases crowding as更多人 prefer public transport
- Weekends have different patterns than weekdays
- Routes serving business districts peak on weekdays
- Routes serving shopping/leisure areas peak on weekends and evenings
- KL rail lines (LRT/MRT) are busiest during weekday rush hours

Respond with ONLY one word: Low, Medium, or Full
"""
        return prompt

    def predict_crowd(self, route_name: str, route_id: str,
                       weather_condition: str = "Clear",
                       temperature: float = 28.0) -> dict:
        """
        Predict crowd level for a route using Gemini API.
        Falls back to rule-based logic if API is unavailable.
        """
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        day_str = now.strftime("%A")

        # Build prompt
        prompt = self.build_prompt(time_str, day_str, weather_condition,
                                   temperature, route_name, route_id)

        # Try Gemini API
        model = self._get_model()
        if model:
            try:
                response = model.generate_content(prompt)
                raw = response.text.strip().upper()
                return self._parse_response(raw, time_str, day_str,
                                            weather_condition, temperature)
            except Exception:
                pass  # Fall through to rule-based

        # Rule-based fallback
        return self._rule_based_fallback(route_id, time_str, day_str,
                                          weather_condition, temperature)

    def _parse_response(self, raw: str, time_str: str, day_str: str,
                        weather: str, temp: float) -> dict:
        """Parse Gemini response into a structured prediction."""
        # Extract the crowd level keyword
        for level in ["FULL", "MEDIUM", "LOW"]:
            if level in raw.upper():
                confidence = 0.85 if level in raw.upper() else 0.7
                return {
                    "crowd_level": level.capitalize(),
                    "confidence": confidence,
                    "time_context": time_str,
                    "day_context": day_str,
                    "weather_context": weather,
                    "temperature": temp,
                    "source": "gemini_api",
                }
        return self._rule_based_fallback(None, time_str, day_str, weather, temp)

    def _rule_based_fallback(self, route_id: Optional[str], time_str: str,
                              day_str: str, weather: str, temp: float) -> dict:
        """Route-aware rule-based crowd prediction when AI is unavailable.
        
        Different routes have different crowd patterns based on their type,
        location, and typical usage.
        """
        hour = int(time_str.split(":")[0])
        is_weekend = day_str.lower() in ("saturday", "sunday")
        is_peak = (7 <= hour <= 9) or (17 <= hour <= 19)
        is_midday = (10 <= hour <= 16)
        is_evening = (20 <= hour <= 23) or (0 <= hour <= 6)
        is_raining = "rain" in weather.lower() or "shower" in weather.lower()

        # Route-specific crowd profiles
        # Each route has a base busyness level and weekend multiplier
        route_profiles = {
            # KL LRT lines - always busy
            "KJL001": {"base": 0.6, "weekend_boost": 0.1, "name": "LRT Kelana Jaya"},
            "KJL002": {"base": 0.5, "weekend_boost": 0.0, "name": "LRT Ampang"},
            "KJL003": {"base": 0.5, "weekend_boost": 0.0, "name": "LRT Sri Petaling"},
            # MRT lines - busy on weekdays, moderate weekends
            "MRT01":  {"base": 0.6, "weekend_boost": -0.1, "name": "MRT Kajang"},
            "MRT02":  {"base": 0.5, "weekend_boost": -0.1, "name": "MRT Putrajaya"},
            # KTM - commuter focused
            "KTM01":  {"base": 0.4, "weekend_boost": -0.2, "name": "KTM Port Klang"},
            "KTM02":  {"base": 0.4, "weekend_boost": -0.2, "name": "KTM Seremban"},
            "KTM03":  {"base": 0.5, "weekend_boost": 0.0, "name": "KTM ETS"},
            # Monorail - tourist area, busy weekends
            "MON01":  {"base": 0.4, "weekend_boost": 0.2, "name": "KL Monorail"},
            # BRT - moderate
            "BRT01":  {"base": 0.3, "weekend_boost": 0.0, "name": "BRT Sunway"},
        }

        profile = route_profiles.get(route_id, {"base": 0.4, "weekend_boost": 0.0, "name": ""})
        logic_score = profile["base"]
        reasons = [f"base crowding for {profile['name']}"]

        # Time adjustments
        if is_weekend:
            logic_score += profile["weekend_boost"]
            if profile["weekend_boost"] > 0:
                reasons.append("busier on weekends (tourist/shopping area)")
            elif profile["weekend_boost"] < 0:
                reasons.append("quieter on weekends (commuter line)")
            else:
                reasons.append("weekend")

            if 10 <= hour <= 18:
                logic_score += 0.15  # Weekend shopping/social hours
                reasons.append("weekend active hours")
            elif hour < 7 or hour > 22:
                logic_score -= 0.2
                reasons.append("late night weekend")
        else:
            # Weekday
            if is_peak:
                logic_score += 0.3
                reasons.append("weekday peak hours")
            elif is_midday:
                logic_score += 0.1
                reasons.append("weekday midday")
            elif is_evening:
                logic_score -= 0.1
                reasons.append("weekday evening")

        # Weather boost
        if is_raining:
            logic_score += 0.15
            reasons.append("rain increases crowding")

        # Clamp and determine level
        logic_score = max(0.0, min(1.0, logic_score))

        if logic_score >= 0.65:
            level = "Full"
            confidence = 0.55 + (min(logic_score, 0.9) * 0.3)
        elif logic_score >= 0.35:
            level = "Medium"
            confidence = 0.55 + (logic_score * 0.3)
        else:
            level = "Low"
            confidence = 0.65 + ((1 - logic_score) * 0.25)

        return {
            "crowd_level": level,
            "confidence": min(confidence, 0.95),
            "time_context": time_str,
            "day_context": day_str,
            "weather_context": weather,
            "temperature": temp,
            "source": "rule_based",
            "reasons": reasons,
        }
