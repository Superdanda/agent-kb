from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.modules.task_board.models.task_rating import RatingDimension


class TaskRatingCreate(BaseModel):
    task_id: str
    rated_agent_id: str
    dimension: RatingDimension
    score: int
    comment: Optional[str] = None


class TaskRatingResponse(BaseModel):
    id: str
    task_id: str
    rater_agent_id: str
    rated_agent_id: str
    dimension: str
    score: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
