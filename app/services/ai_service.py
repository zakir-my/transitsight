"""AI prediction service - integrates with Google AI Studio (Gemini API)."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

KL_TZ = ZoneInfo("Asia/Kuala_Lumpur")
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
                     temperature: float, route_name: str, route_id: str,
                     feedback_context: Optional[str] = None) -> str:
        """
        Build a structured prompt for the Gemini API.
        The prompt asks the AI to classify crowd level based on contextual variables
        and optionally includes real user feedback for self-correction.
        """
        feedback_line = ""
        if feedback_context:
            feedback_line = f"\n{feedback_context}\n"

        prompt = f"""You are TransitSight, a smart public transport crowd predictor for Malaysia.
Your task is to predict the crowd level for a transit route based on the following context.

Context:
- Route: {route_name} ({route_id})
- Time: {time}
- Day: {day}
- Weather: {weather_condition}
- Temperature: {temperature}°C
{feedback_line}
Based on your knowledge of typical crowd patterns in Malaysian public transit,
classify the expected crowd level as exactly one of: Low, Medium, or Full.

Consider these factors:
- Peak hours (7-9 AM, 5-7 PM weekdays) tend to be Medium to Full
- Midday and late evening tend to be Low to Medium
- Rainy weather often increases crowding as more people prefer public transport
- Weekends have different patterns than weekdays
- Routes serving business districts peak on weekdays
- Routes serving shopping/leisure areas peak on weekends and evenings
- KL rail lines (LRT/MRT) are busiest during weekday rush hours
- The user feedback data above represents what commuters actually reported — use it as ground truth calibration

Respond with ONLY one word: Low, Medium, or Full
"""
        return prompt

    def predict_crowd(self, route_name: str, route_id: str,
                       weather_condition: str = "Clear",
                       temperature: float = 28.0) -> dict:
        """
        Predict crowd level for a route using Gemini API.
        Incorporates real user feedback for self-correction.
        Falls back to rule-based logic if API is unavailable.
        """
        now = datetime.now(KL_TZ)
        time_str = now.strftime("%H:%M")
        day_str = now.strftime("%A")

        # Get feedback context for this route
        feedback_context = self._get_feedback_context(route_id)

        # Build prompt with feedback
        prompt = self.build_prompt(time_str, day_str, weather_condition,
                                   temperature, route_name, route_id,
                                   feedback_context)

        # Try Gemini API
        model = self._get_model()
        if model:
            try:
                response = model.generate_content(prompt)
                raw = response.text.strip().upper()
                return self._parse_response(raw, time_str, day_str,
                                            weather_condition, temperature,
                                            feedback_context)
            except Exception:
                pass  # Fall through to rule-based

        # Rule-based fallback (now also feedback-aware)
        return self._rule_based_fallback(route_id, time_str, day_str,
                                          weather_condition, temperature,
                                          feedback_context)

    def _get_feedback_context(self, route_id: str) -> Optional[str]:
        """Query feedback stats for a route and format as prompt context."""
        try:
            from app.services.feedback_service import FeedbackService
            stats = FeedbackService.get_route_stats(route_id)
            if stats["total_feedback"] > 0:
                breakdown = stats["breakdown"]
                low = breakdown.get("Low", 0)
                med = breakdown.get("Medium", 0)
                full = breakdown.get("Full", 0)
                total = stats["total_feedback"]
                accuracy = stats["accuracy_pct"]
                acc_line = f" (prediction accuracy: {accuracy}%)" if accuracy else ""
                return (
                    f"- 📊 User feedback for this route: {total} report{'' if total == 1 else 's'}"
                    f"{acc_line}\n"
                    f"  - Low: {low}  |  Medium: {med}  |  Full: {full}"
                )
        except Exception:
            pass
        return None

    def _parse_response(self, raw: str, time_str: str, day_str: str,
                        weather: str, temp: float,
                        feedback_context: Optional[str] = None) -> dict:
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
        return self._rule_based_fallback(None, time_str, day_str, weather, temp, feedback_context)

    def _rule_based_fallback(self, route_id: Optional[str], time_str: str,
                              day_str: str, weather: str, temp: float,
                              feedback_context: Optional[str] = None) -> dict:
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

        # Feedback-based calibration
        # Parse the feedback_context to adjust prediction based on real user reports
        if feedback_context:
            try:
                # Extract numbers: "Low: 2  |  Medium: 3  |  Full: 5"
                import re
                low_m = re.search(r"Low:\s*(\d+)", feedback_context)
                med_m = re.search(r"Medium:\s*(\d+)", feedback_context)
                full_m = re.search(r"Full:\s*(\d+)", feedback_context)
                low = int(low_m.group(1)) if low_m else 0
                med = int(med_m.group(1)) if med_m else 0
                full = int(full_m.group(1)) if full_m else 0
                total_fb = low + med + full

                if total_fb > 0:
                    # Calculate feedback-weighted score (0 to 1)
                    fb_score = (low * 0.0 + med * 0.5 + full * 1.0) / total_fb
                    # Blend: 70% rule-based + 30% feedback
                    logic_score = (logic_score * 0.7) + (fb_score * 0.3)
                    reasons.append(f"calibrated with {total_fb} user report{'s' if total_fb != 1 else ''}")
            except Exception:
                pass  # If parsing fails, just use unadjusted score

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
