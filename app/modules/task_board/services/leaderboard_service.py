import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.modules.task_board.models.leaderboard import Leaderboard, LeaderboardPeriod
from app.modules.task_board.models.task import Task, TaskStatus
from app.modules.task_board.models.task_rating import TaskRating
from app.core.exceptions import ResourceNotFoundError


# 积分规则
BASE_POINTS = 10

PRIORITY_BONUS = {
    "URGENT": 8,
    "HIGH": 5,
    "MEDIUM": 3,
    "LOW": 0,
}

DIFFICULTY_BONUS = {
    "EXPERT": 10,
    "HARD": 6,
    "MEDIUM": 3,
    "EASY": 0,
}


class LeaderboardService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_task_points(self, task: Task) -> int:
        """计算任务积分"""
        points = task.points or BASE_POINTS
        
        # 优先级加成
        if task.priority and hasattr(task.priority, 'value'):
            priority_value = task.priority.value
        else:
            priority_value = str(task.priority)
        points += PRIORITY_BONUS.get(priority_value, 0)
        
        # 难度加成
        if task.difficulty and hasattr(task.difficulty, 'value'):
            difficulty_value = task.difficulty.value
        else:
            difficulty_value = str(task.difficulty) if task.difficulty else None
        if difficulty_value:
            points += DIFFICULTY_BONUS.get(difficulty_value, 0)
        
        return points
    
    def calculate_rating_bonus(self, agent_id: str, period_start: datetime, period_end: datetime) -> int:
        """计算评分加成"""
        ratings = self.db.query(TaskRating).filter(
            TaskRating.rated_agent_id == agent_id,
            TaskRating.created_at >= period_start,
            TaskRating.created_at <= period_end,
        ).all()
        
        if not ratings:
            return 0
        
        total_score = sum(r.score for r in ratings)
        avg_score = total_score / len(ratings)
        
        # 评分加成 = 平均分 * 2
        return int(avg_score * 2)
    
    def update_on_task_complete(self, task_id: str) -> dict:
        """任务确认完成时更新排行榜"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        if task.status != TaskStatus.CONFIRMED:
            return {"error": "Task is not in CONFIRMED status"}
        
        if not task.assigned_to_agent_id:
            return {"error": "Task has no assigned agent"}
        
        now = datetime.now(timezone.utc)
        
        # 更新所有周期的排行榜
        periods_to_update = [
            LeaderboardPeriod.DAILY,
            LeaderboardPeriod.WEEKLY,
            LeaderboardPeriod.MONTHLY,
            LeaderboardPeriod.ALL_TIME,
        ]
        
        results = {}
        for period in periods_to_update:
            period_start, period_end = self._get_period_bounds(now, period)
            
            # 计算积分
            task_points = self.calculate_task_points(task)
            rating_bonus = self.calculate_rating_bonus(
                task.assigned_to_agent_id, period_start, period_end
            )
            total_points = task_points + rating_bonus
            
            # 更新或创建排行榜记录
            entry = self.db.query(Leaderboard).filter(
                Leaderboard.agent_id == task.assigned_to_agent_id,
                Leaderboard.period == period.value,
                Leaderboard.period_start == period_start,
                Leaderboard.period_end == period_end,
            ).first()
            
            if entry:
                entry.score += total_points
                entry.tasks_completed += 1
                entry.total_points = entry.score
            else:
                entry = Leaderboard(
                    id=str(uuid.uuid4()),
                    agent_id=task.assigned_to_agent_id,
                    period=period.value,
                    period_start=period_start,
                    period_end=period_end,
                    rank=0,  # 稍后重新计算
                    score=total_points,
                    tasks_completed=1,
                    total_points=total_points,
                )
                self.db.add(entry)
            
            results[period.value] = total_points
        
        self.db.commit()
        
        # 重新计算所有排行榜的排名
        self._recalculate_all_ranks()
        
        return {
            "task_id": task_id,
            "agent_id": task.assigned_to_agent_id,
            "points_by_period": results,
        }
    
    def _get_period_bounds(self, now: datetime, period: LeaderboardPeriod) -> Tuple[datetime, datetime]:
        """计算指定周期的起止时间"""
        if period == LeaderboardPeriod.DAILY:
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == LeaderboardPeriod.WEEKLY:
            days_since_monday = now.weekday()
            period_start = (now.replace(hour=0, minute=0, second=0, microsecond=0)
                          .replace(day=now.day - days_since_monday))
            period_end = period_start.replace(day=period_start.day + 6,
                                             hour=23, minute=59, second=59)
        elif period == LeaderboardPeriod.MONTHLY:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                period_end = now.replace(year=now.year + 1, month=1, day=1,
                                        hour=0, minute=0, second=0) - timezone.utc
            else:
                period_end = now.replace(month=now.month + 1, day=1,
                                        hour=0, minute=0, second=0) - timezone.utc
        else:  # ALL_TIME
            period_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
            period_end = now
        
        return period_start, period_end
    
    def _recalculate_all_ranks(self):
        """重新计算所有排行榜的排名"""
        for period in LeaderboardPeriod:
            entries = self.db.query(Leaderboard).filter(
                Leaderboard.period == period.value
            ).order_by(Leaderboard.score.desc()).all()
            
            for rank, entry in enumerate(entries, 1):
                entry.rank = rank
            
            self.db.commit()

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
    
    def get_leaderboard_simple(self, period: LeaderboardPeriod, limit: int = 10) -> List[dict]:
        """获取排行榜（简化版，按rank排序）"""
        entries = self.db.query(Leaderboard).filter(
            Leaderboard.period == period.value
        ).order_by(Leaderboard.rank).limit(limit).all()
        
        return [
            {
                "rank": e.rank,
                "agent_id": e.agent_id,
                "tasks_completed": e.tasks_completed,
                "total_points": e.total_points,
                "avg_rating": e.avg_rating,
            }
            for e in entries
        ]
    
    def get_agent_rank_simple(self, agent_id: str, period: LeaderboardPeriod) -> Optional[dict]:
        """获取指定 Agent 的排名（简化版）"""
        entry = self.db.query(Leaderboard).filter(
            Leaderboard.agent_id == agent_id,
            Leaderboard.period == period.value,
        ).first()
        
        if not entry:
            return None
        
        return {
            "rank": entry.rank,
            "agent_id": entry.agent_id,
            "tasks_completed": entry.tasks_completed,
            "total_points": entry.total_points,
            "avg_rating": entry.avg_rating,
        }
