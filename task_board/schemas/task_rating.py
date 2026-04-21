from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.task_board.models.task_rating import RatingDimension


class TaskRatingCreate(BaseModel):
    task_id: str
    rated_agent_id: str
    dimension: RatingDimension
    score: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class TaskRatingUpdate(BaseModel):
    score: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class TaskRatingResponse(BaseModel):
    id: str
    task_id: str
    rater_agent_id: str
    rated_agent_id: str
    dimension: str
    score: int
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
