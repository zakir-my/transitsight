"""Feedback service - manages user crowd validation feedback."""

from datetime import datetime
from typing import Optional
from app.database import get_db


class FeedbackService:
    """Manages user feedback collection, storage, and analytics."""

    @staticmethod
    def submit_feedback(route_id: str, predicted_level: str,
                        reported_level: str, user_id: str = "anonymous",
                        comment: str = "") -> dict:
        """Store user feedback about a crowd prediction."""
        with get_db() as conn:
            cursor = conn.execute(
                """INSERT INTO feedback (route_id, user_id, predicted_level, reported_level, comment)
                   VALUES (?, ?, ?, ?, ?)""",
                (route_id, user_id, predicted_level, reported_level, comment),
            )

            # Update user feedback count
            cursor2 = conn.execute(
                """UPDATE users SET feedback_count = feedback_count + 1
                   WHERE user_id = ?""",
                (user_id,),
            )
            if cursor2.rowcount == 0:
                conn.execute(
                    "INSERT OR IGNORE INTO users (user_id, name, role) VALUES (?, ?, 'commuter')",
                    (user_id, user_id),
                )
                conn.execute(
                    "UPDATE users SET feedback_count = 1 WHERE user_id = ?",
                    (user_id,),
                )

            # Get streak for gamification
            streak_row = conn.execute(
                "SELECT feedback_count, streak FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            streak = streak_row["streak"] if streak_row else 0
            total = streak_row["feedback_count"] if streak_row else 0

            return {
                "status": "submitted",
                "feedback_id": cursor.lastrowid,
                "streak": streak,
                "total_feedback": total,
                "message": f"Thanks! You've submitted {total} report{'s' if total != 1 else ''}. Streak: {streak} 🔥",
            }

    @staticmethod
    def get_route_stats(route_id: str) -> dict:
        """Get feedback statistics for a specific route."""
        with get_db() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE route_id = ?",
                (route_id,),
            ).fetchone()[0]

            by_level = conn.execute(
                """SELECT reported_level, COUNT(*) as count
                   FROM feedback WHERE route_id = ?
                   GROUP BY reported_level""",
                (route_id,),
            ).fetchall()

            accuracy = conn.execute(
                """SELECT
                     CAST(SUM(CASE WHEN predicted_level = reported_level THEN 1 ELSE 0 END) AS REAL)
                     / NULLIF(COUNT(*), 0) * 100 as accuracy_pct
                   FROM feedback WHERE route_id = ?""",
                (route_id,),
            ).fetchone()[0]

            return {
                "route_id": route_id,
                "total_feedback": total,
                "breakdown": {row["reported_level"]: row["count"] for row in by_level},
                "accuracy_pct": round(accuracy, 1) if accuracy else None,
            }

    @staticmethod
    def get_all_stats() -> dict:
        """Get overall feedback statistics for admin dashboard."""
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            total_users = conn.execute(
                "SELECT COUNT(DISTINCT user_id) FROM feedback"
            ).fetchone()[0]

            # Accuracy over time (last 7 days)
            recent = conn.execute(
                """SELECT
                     DATE(created_at) as date,
                     COUNT(*) as count,
                     CAST(SUM(CASE WHEN predicted_level = reported_level THEN 1 ELSE 0 END) AS REAL)
                     / NULLIF(COUNT(*), 0) * 100 as accuracy
                   FROM feedback
                   WHERE created_at >= DATE('now', '-7 days')
                   GROUP BY DATE(created_at)
                   ORDER BY date"""
            ).fetchall()

            # Per-route breakdown
            by_route = conn.execute(
                """SELECT r.route_name, f.route_id, COUNT(*) as count
                   FROM feedback f
                   JOIN routes r ON f.route_id = r.route_id
                   GROUP BY f.route_id
                   ORDER BY count DESC"""
            ).fetchall()

            return {
                "total_feedback": total,
                "total_users": total_users,
                "recent_accuracy": [dict(r) for r in recent],
                "by_route": [dict(r) for r in by_route],
            }

    @staticmethod
    def get_user_streak(user_id: str) -> int:
        """Get feedback streak count for a user (gamification)."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT streak, feedback_count FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row:
                return row["streak"]
            return 0
