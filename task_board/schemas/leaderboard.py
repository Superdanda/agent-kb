from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.task_board.models.leaderboard import LeaderboardPeriod


class LeaderboardResponse(BaseModel):
    id: str
    agent_id: str
    period: str
    period_start: datetime
    period_end: datetime
    rank: int
    score: int
    tasks_completed: int
    total_points: int
    avg_rating: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaderboardQuery(BaseModel):
    period: LeaderboardPeriod = LeaderboardPeriod.WEEKLY
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
