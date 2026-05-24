"""Route service - manages transit route information."""

from typing import Optional
from app.database import get_db


class RouteService:
    """Manages route data including cached GTFS data."""

    @staticmethod
    def get_all_routes() -> list:
        """Get all available routes from the database."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM routes WHERE is_active = 1 ORDER BY route_name"
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_route(route_id: str) -> Optional[dict]:
        """Get a single route by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM routes WHERE route_id = ?", (route_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def search_routes(query: str) -> list:
        """Search routes by name or ID."""
        with get_db() as conn:
            pattern = f"%{query}%"
            rows = conn.execute(
                """SELECT * FROM routes
                   WHERE (route_name LIKE ? OR route_id LIKE ?)
                   AND is_active = 1
                   ORDER BY route_name
                   LIMIT 20""",
                (pattern, pattern),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_recent_predictions(route_id: str, limit: int = 10) -> list:
        """Get recent predictions for a route."""
        with get_db() as conn:
            rows = conn.execute(
                """SELECT * FROM predictions
                   WHERE route_id = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (route_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
