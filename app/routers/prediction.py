"""Prediction API routes."""

from fastapi import APIRouter, HTTPException, Query
from app.services.ai_service import AIPredictionService
from app.services.weather_service import WeatherService
from app.services.transit_service import TransitDataService
from app.services.route_service import RouteService
from app.database import get_db
from datetime import datetime

router = APIRouter(prefix="/api", tags=["Prediction"])
ai_service = AIPredictionService()


@router.get("/predict")
async def predict_crowd(route_id: str = Query(..., description="Route ID to predict")):
    """
    Get crowd prediction for a specific route.
    Fetches weather context, builds AI prompt, and returns crowd level.
    """
    # Get route info
    route = RouteService.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Fetch weather context
    weather = WeatherService.fetch_current_weather()

    # Get AI prediction
    prediction = ai_service.predict_crowd(
        route_name=route["route_name"],
        route_id=route["route_id"],
        weather_condition=weather.get("condition", "Clear"),
        temperature=weather.get("temperature", 28.0),
    )

    # Store prediction in database
    with get_db() as conn:
        conn.execute(
            """INSERT INTO predictions
               (route_id, crowd_level, confidence, time_context, day_context,
                weather_context, temperature)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (route_id, prediction["crowd_level"], prediction.get("confidence", 0.7),
             prediction["time_context"], prediction["day_context"],
             prediction["weather_context"], prediction.get("temperature")),
        )

    return {
        "route": {
            "route_id": route["route_id"],
            "route_name": route["route_name"],
            "color": route.get("color", "#2196F3"),
            "agency": route.get("agency", ""),
        },
        "prediction": prediction,
        "weather": weather,
    }


@router.get("/routes")
async def get_routes(search: str = Query(None, description="Search query")):
    """Get list of available transit routes."""
    if search:
        routes = RouteService.search_routes(search)
    else:
        routes = RouteService.get_all_routes()
    return {"routes": routes}


@router.get("/routes/{route_id}")
async def get_route_detail(route_id: str):
    """Get route details with recent predictions."""
    route = RouteService.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    predictions = RouteService.get_recent_predictions(route_id, limit=10)
    return {"route": route, "recent_predictions": predictions}


@router.get("/recommend")
async def travel_recommendation(route_id: str = Query(..., description="Route ID")):
    """
    Travel recommendation (UC002).
    Compares crowd predictions across different times of day
    and recommends the least crowded window.
    """
    from app.services.ai_service import AIPredictionService
    from app.services.weather_service import WeatherService

    route = RouteService.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    weather = WeatherService.fetch_current_weather()

    service = AIPredictionService()
    now = datetime.now()

    time_slots = [
        ("morning", "07:30"),
        ("midday", "12:30"),
        ("afternoon", "15:00"),
        ("evening", "18:00"),
        ("late_night", "21:30"),
    ]

    results = []
    for slot_name, slot_time in time_slots:
        pred = service._rule_based_fallback(
            route_id=route_id,
            time_str=slot_time,
            day_str=now.strftime("%A"),
            weather=weather.get("condition", "Clear"),
            temp=weather.get("temperature", 28.0),
            feedback_context=service._get_feedback_context(route_id),
        )
        results.append({
            "slot": slot_name,
            "time": slot_time,
            "crowd_level": pred["crowd_level"],
            "confidence": pred.get("confidence", 0.7),
        })

    # Find best slot (lowest crowding)
    level_order = {"Low": 0, "Medium": 1, "Full": 2}
    sorted_slots = sorted(results, key=lambda r: level_order.get(r["crowd_level"], 99))
    best = sorted_slots[0] if sorted_slots else None

    return {
        "route_id": route_id,
        "route_name": route["route_name"],
        "today_weather": {
            "condition": weather.get("condition", "Clear"),
            "temperature": weather.get("temperature", 28.0),
        },
        "recommendation": best,
        "time_slots": results,
    }