from datetime import datetime
from typing import Optional
from pydantic import BaseModel
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
    avg_rating: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
