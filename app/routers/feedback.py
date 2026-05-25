"""Feedback API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/api", tags=["Feedback"])


class FeedbackCreate(BaseModel):
    route_id: str
    predicted_level: str
    reported_level: str
    user_id: str = "anonymous"
    comment: str = ""


@router.post("/feedback")
async def submit_feedback(feedback: FeedbackCreate):
    """Submit crowd validation feedback."""
    # Validate levels
    valid_levels = {"Low", "Medium", "Full"}
    if feedback.predicted_level not in valid_levels:
        raise HTTPException(status_code=400, detail="Invalid predicted_level")
    if feedback.reported_level not in valid_levels:
        raise HTTPException(status_code=400, detail="Invalid reported_level")

    result = FeedbackService.submit_feedback(
        route_id=feedback.route_id,
        predicted_level=feedback.predicted_level,
        reported_level=feedback.reported_level,
        user_id=feedback.user_id,
        comment=feedback.comment,
    )
    return result


@router.get("/feedback/stats/{route_id}")
async def get_feedback_stats(route_id: str):
    """Get feedback statistics for a route."""
    return FeedbackService.get_route_stats(route_id)


@router.get("/feedback/user/{user_id}")
async def get_user_streak(user_id: str):
    """Get user feedback streak."""
    streak = FeedbackService.get_user_streak(user_id)
    return {"user_id": user_id, "streak": streak}


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str):
    """Get user profile with feedback history."""
    from app.database import get_db

    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

        feedbacks = conn.execute(
            """SELECT f.*, r.route_name
               FROM feedback f
               JOIN routes r ON f.route_id = r.route_id
               WHERE f.user_id = ?
               ORDER BY f.created_at DESC LIMIT 20""",
            (user_id,),
        ).fetchall()

        # Accuracy of user's feedback
        accuracy = conn.execute(
            """SELECT
                 CAST(SUM(CASE WHEN predicted_level = reported_level THEN 1 ELSE 0 END) AS REAL)
                 / NULLIF(COUNT(*), 0) * 100 as accuracy_pct,
                 COUNT(*) as total
               FROM feedback WHERE user_id = ?""",
            (user_id,),
        ).fetchone()

    total_fb = accuracy["total"] if accuracy else 0
    acc_val = round(accuracy["accuracy_pct"], 1) if accuracy and accuracy["accuracy_pct"] else None

    return {
        "user_id": user_id,
        "streak": user["streak"] if user else 0,
        "total_feedback": total_fb,
        "accuracy_pct": acc_val,
        "role": user["role"] if user else "commuter",
        "feedback_history": [
            {
                "route_name": f["route_name"],
                "route_id": f["route_id"],
                "predicted_level": f["predicted_level"],
                "reported_level": f["reported_level"],
                "created_at": f["created_at"],
            }
            for f in feedbacks
        ],
    }
