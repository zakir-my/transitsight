"""Admin API routes."""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from app.services.feedback_service import FeedbackService
from app.services.transit_service import TransitDataService
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def verify_admin(authorization: str = Header(None)):
    """Simple bearer token auth for admin endpoints."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    # Accept admin:admin123 in base64 or plain
    import base64
    try:
        if authorization.startswith("Basic "):
            decoded = base64.b64decode(authorization[6:]).decode()
            username, password = decoded.split(":", 1)
            if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
                return True
    except Exception:
        pass
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/dashboard")
async def admin_dashboard(auth=Depends(verify_admin)):
    """Get admin dashboard data: feedback stats, prediction counts, API health."""
    stats = FeedbackService.get_all_stats()

    with get_db() as conn:
        # Prediction counts
        pred_count = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]

        # Today's predictions
        today_count = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE DATE(created_at) = DATE('now')"
        ).fetchone()[0]

        # Total routes
        route_count = conn.execute(
            "SELECT COUNT(*) FROM routes WHERE is_active = 1"
        ).fetchone()[0]

        # Recent feedback entries
        recent_feedback = conn.execute(
            """SELECT f.*, r.route_name
               FROM feedback f
               JOIN routes r ON f.route_id = r.route_id
               ORDER BY f.created_at DESC LIMIT 10"""
        ).fetchall()

        # Crowd level distribution
        crowd_dist = conn.execute(
            """SELECT crowd_level, COUNT(*) as count
               FROM predictions
               GROUP BY crowd_level"""
        ).fetchall()

    return {
        "stats": stats,
        "predictions_total": pred_count,
        "predictions_today": today_count,
        "routes_total": route_count,
        "recent_feedback": [dict(r) for r in recent_feedback],
        "crowd_distribution": {r["crowd_level"]: r["count"] for r in crowd_dist},
    }


@router.get("/api-health")
async def api_health(auth=Depends(verify_admin)):
    """Check external API health status."""
    import time
    import requests

    results = []

    # Check data.gov.my GTFS
    for name, url in [
        ("GTFS Static (KTMB)", f"{settings.GTFS_STATIC_BASE_URL}/ktmb"),
        ("Weather API", settings.WEATHER_BASE_URL),
    ]:
        try:
            start = time.time()
            resp = requests.get(url, timeout=10)
            elapsed = int((time.time() - start) * 1000)
            results.append({
                "service": name,
                "status": "up" if resp.status_code == 200 else "degraded",
                "response_time_ms": elapsed,
                "http_status": resp.status_code,
            })
        except Exception as e:
            results.append({
                "service": name,
                "status": "down",
                "error": str(e),
            })

    # Check Gemini API
    if settings.GEMINI_API_KEY:
        results.append({
            "service": "Gemini API",
            "status": "configured",
            "note": "API key is set (test on first prediction call)",
        })
    else:
        results.append({
            "service": "Gemini API",
            "status": "not_configured",
            "note": "Set GEMINI_API_KEY in .env",
        })

    return {"services": results}


@router.post("/routes/refresh")
async def refresh_routes(auth=Depends(verify_admin)):
    """Refresh route data from GTFS API."""
    try:
        gtfs_data = TransitDataService.fetch_static_gtfs("ktmb")
        return {
            "status": "refreshed",
            "routes_fetched": len(gtfs_data.get("routes", [])),
            "message": "Route data refreshed from GTFS API",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
