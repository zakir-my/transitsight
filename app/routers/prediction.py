"""Prediction API routes."""

from fastapi import APIRouter, HTTPException, Query
from app.services.ai_service import AIPredictionService
from app.services.weather_service import WeatherService
from app.services.transit_service import TransitDataService
from app.services.route_service import RouteService
from app.database import get_db

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
