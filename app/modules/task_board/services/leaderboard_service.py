import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.modules.task_board.models.leaderboard import Leaderboard, LeaderboardPeriod
from app.modules.task_board.models.task import Task, TaskStatus
from app.core.exceptions import ResourceNotFoundError


class LeaderboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_leaderboard(
        self,
        period: LeaderboardPeriod,
        period_start: datetime,
        period_end: datetime,
        limit: int = 50,
    ) -> List[Leaderboard]:
        return (
            self.db.query(Leaderboard)
            .filter(
                Leaderboard.period == period.value,
                Leaderboard.period_start == period_start,
                Leaderboard.period_end == period_end,
            )
            .order_by(Leaderboard.rank)
            .limit(limit)
            .all()
        )

    def get_agent_leaderboard_entry(
        self,
        agent_id: str,
        period: LeaderboardPeriod,
        period_start: datetime,
        period_end: datetime,
    ) -> Optional[Leaderboard]:
        return (
            self.db.query(Leaderboard)
            .filter(
                Leaderboard.agent_id == agent_id,
                Leaderboard.period == period.value,
                Leaderboard.period_start == period_start,
                Leaderboard.period_end == period_end,
            )
            .first()
        )

    def get_agent_rank_history(
        self,
        agent_id: str,
        period: Optional[LeaderboardPeriod] = None,
        limit: int = 20,
    ) -> List[Leaderboard]:
        query = self.db.query(Leaderboard).filter(Leaderboard.agent_id == agent_id)

        if period:
            query = query.filter(Leaderboard.period == period.value)

        return query.order_by(desc(Leaderboard.period_end)).limit(limit).all()

    def calculate_and_update_leaderboard(
        self,
        period: LeaderboardPeriod,
        period_start: datetime,
        period_end: datetime,
    ) -> List[Leaderboard]:
        tasks_completed = (
            self.db.query(
                Task.assigned_to_agent_id,
                func.count(Task.id).label("task_count"),
                func.sum(Task.points).label("total_points"),
            )
            .filter(
                Task.assigned_to_agent_id.isnot(None),
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= period_start,
                Task.completed_at <= period_end,
            )
            .group_by(Task.assigned_to_agent_id)
            .all()
        )

        rankings = []
        for rank, entry in enumerate(sorted(tasks_completed, key=lambda x: x.total_points or 0, reverse=True), start=1):
            leaderboard_entry = self.get_agent_leaderboard_entry(
                entry.assigned_to_agent_id, period, period_start, period_end
            )

            if leaderboard_entry:
                leaderboard_entry.rank = rank
                leaderboard_entry.score = entry.total_points or 0
                leaderboard_entry.tasks_completed = entry.task_count
                leaderboard_entry.total_points = entry.total_points or 0
                leaderboard_entry.updated_at = datetime.now(timezone.utc)
            else:
                leaderboard_entry = Leaderboard(
                    id=str(uuid.uuid4()),
                    agent_id=entry.assigned_to_agent_id,
                    period=period.value,
                    period_start=period_start,
                    period_end=period_end,
                    rank=rank,
                    score=entry.total_points or 0,
                    tasks_completed=entry.task_count,
                    total_points=entry.total_points or 0,
                )
                self.db.add(leaderboard_entry)

            rankings.append(leaderboard_entry)

        self.db.commit()
        for entry in rankings:
            self.db.refresh(entry)

        return rankings

    def get_top_agents(
        self,
        period: LeaderboardPeriod,
        limit: int = 10,
    ) -> List[Leaderboard]:
        latest_entries = (
            self.db.query(
                Leaderboard.agent_id,
                func.max(Leaderboard.period_end).label("latest_period_end"),
            )
            .filter(Leaderboard.period == period.value)
            .group_by(Leaderboard.agent_id)
            .subquery()
        )

        return (
            self.db.query(Leaderboard)
            .join(
                latest_entries,
                (Leaderboard.agent_id == latest_entries.c.agent_id)
                & (Leaderboard.period_end == latest_entries.c.latest_period_end),
            )
            .filter(Leaderboard.period == period.value)
            .order_by(Leaderboard.rank)
            .limit(limit)
            .all()
        )

    def get_agent_stats(self, agent_id: str) -> dict:
        total_tasks = (
            self.db.query(func.count(Task.id))
            .filter(Task.assigned_to_agent_id == agent_id, Task.status == TaskStatus.COMPLETED)
            .scalar()
        )

        total_points = (
            self.db.query(func.sum(Task.points))
            .filter(Task.assigned_to_agent_id == agent_id, Task.status == TaskStatus.COMPLETED)
            .scalar()
        )

        current_rank = (
            self.db.query(Leaderboard)
            .filter(
                Leaderboard.agent_id == agent_id,
                Leaderboard.period == LeaderboardPeriod.ALL_TIME.value,
            )
            .first()
        )

        return {
            "total_tasks_completed": total_tasks or 0,
            "total_points": total_points or 0,
            "current_rank": current_rank.rank if current_rank else None,
            "current_score": current_rank.score if current_rank else 0,
        }
