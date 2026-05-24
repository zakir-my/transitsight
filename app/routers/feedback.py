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
