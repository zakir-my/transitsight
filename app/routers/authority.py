"""Authority API routes - public read-only transit analytics."""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional
from app.database import get_db

router = APIRouter(prefix="/api/authority", tags=["Authority"])


@router.get("/dashboard")
async def authority_dashboard():
    """Get public transit authority dashboard data (no auth required)."""
    with get_db() as conn:
        # Total predictions
        total_preds = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]

        # Predictions today
        today_preds = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE DATE(created_at) = DATE('now')"
        ).fetchone()[0]

        # Total routes
        total_routes = conn.execute(
            "SELECT COUNT(*) FROM routes WHERE is_active = 1"
        ).fetchone()[0]

        # Total feedback
        total_feedback = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]

        # Route-level summaries
        route_summaries = conn.execute("""
            SELECT
                r.route_id,
                r.route_name,
                r.agency,
                r.color,
                COUNT(p.id) as prediction_count,
                COALESCE(AVG(CASE
                    WHEN p.crowd_level = 'Full' THEN 1.0
                    WHEN p.crowd_level = 'Medium' THEN 0.5
                    WHEN p.crowd_level = 'Low' THEN 0.0
                END), 0) as avg_crowd_score,
                (SELECT crowd_level FROM predictions
                 WHERE route_id = r.route_id
                 ORDER BY created_at DESC LIMIT 1) as latest_level
            FROM routes r
            LEFT JOIN predictions p ON r.route_id = p.route_id
            WHERE r.is_active = 1
            GROUP BY r.route_id
            ORDER BY avg_crowd_score DESC
        """).fetchall()

        # Peak hour congestion (group by hour)
        peak_hours = conn.execute("""
            SELECT
                CAST(strftime('%H', time_context) AS INTEGER) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN crowd_level = 'Full' THEN 1 ELSE 0 END) as full_count,
                SUM(CASE WHEN crowd_level = 'Medium' THEN 1 ELSE 0 END) as med_count
            FROM predictions
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY hour
            ORDER BY hour
        """).fetchall()

        # Crowd level distribution (public)
        crowd_dist = conn.execute("""
            SELECT crowd_level, COUNT(*) as count
            FROM predictions
            GROUP BY crowd_level
        """).fetchall()

        # Prediction accuracy (last 7 days rolling)
        accuracy_trend = conn.execute("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as count,
                CAST(SUM(CASE WHEN predicted_level = reported_level THEN 1 ELSE 0 END) AS REAL)
                / NULLIF(COUNT(*), 0) * 100 as accuracy
            FROM feedback
            WHERE created_at >= DATE('now', '-14 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """).fetchall()

    return {
        "total_predictions": total_preds,
        "predictions_today": today_preds,
        "total_routes": total_routes,
        "total_feedback": total_feedback,
        "route_summaries": [
            {
                "route_id": r["route_id"],
                "route_name": r["route_name"],
                "agency": r["agency"],
                "color": r["color"],
                "prediction_count": r["prediction_count"],
                "avg_crowd_score": round(r["avg_crowd_score"], 2),
                "latest_level": r["latest_level"],
            }
            for r in route_summaries
        ],
        "peak_hours": [
            {
                "hour": r["hour"],
                "total": r["total"],
                "full_pct": round(r["full_count"] / r["total"] * 100, 1) if r["total"] > 0 else 0,
                "crowded_pct": round((r["full_count"] + r["med_count"]) / r["total"] * 100, 1) if r["total"] > 0 else 0,
            }
            for r in peak_hours
        ],
        "crowd_distribution": {r["crowd_level"]: r["count"] for r in crowd_dist},
        "accuracy_trend": [dict(r) for r in accuracy_trend],
    }


@router.get("/routes/{route_id}/trends")
async def route_trends(route_id: str):
    """Get detailed trend data for a specific route."""
    with get_db() as conn:
        # Check route exists
        route = conn.execute(
            "SELECT * FROM routes WHERE route_id = ?", (route_id,)
        ).fetchone()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

        # Hourly pattern for this route
        hourly = conn.execute("""
            SELECT
                CAST(strftime('%H', time_context) AS INTEGER) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN crowd_level = 'Full' THEN 1 ELSE 0 END) as full_count,
                SUM(CASE WHEN crowd_level = 'Medium' THEN 1 ELSE 0 END) as med_count
            FROM predictions
            WHERE route_id = ? AND created_at >= DATE('now', '-14 days')
            GROUP BY hour
            ORDER BY hour
        """, (route_id,)).fetchall()

        # Day-of-week pattern
        dow = conn.execute("""
            SELECT
                day_context as day,
                COUNT(*) as total,
                SUM(CASE WHEN crowd_level = 'Full' THEN 1 ELSE 0 END) as full_count
            FROM predictions
            WHERE route_id = ? AND created_at >= DATE('now', '-30 days')
            GROUP BY day_context
            ORDER BY
                CASE day_context
                    WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
                    WHEN 'Sunday' THEN 7
                END
        """, (route_id,)).fetchall()

        # Recent predictions
        recent = conn.execute("""
            SELECT crowd_level, confidence, time_context, day_context,
                   weather_context, created_at
            FROM predictions
            WHERE route_id = ?
            ORDER BY created_at DESC LIMIT 20
        """, (route_id,)).fetchall()

    return {
        "route": dict(route),
        "hourly_pattern": [
            {
                "hour": r["hour"],
                "total": r["total"],
                "full_pct": round(r["full_count"] / r["total"] * 100, 1) if r["total"] > 0 else 0,
                "crowded_pct": round((r["full_count"] + r["med_count"]) / r["total"] * 100, 1) if r["total"] > 0 else 0,
            }
            for r in hourly
        ],
        "day_of_week": [
            {
                "day": r["day"],
                "total": r["total"],
                "full_pct": round(r["full_count"] / r["total"] * 100, 1) if r["total"] > 0 else 0,
            }
            for r in dow
        ],
        "recent_predictions": [dict(r) for r in recent],
    }
