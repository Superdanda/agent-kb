from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.modules.task_board.models.leaderboard import Leaderboard, LeaderboardPeriod
from app.modules.task_board.models.task import Task, TaskStatus
from app.modules.task_board.models.task_rating import TaskRating

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("")
def get_leaderboard(
    period: LeaderboardPeriod = LeaderboardPeriod.WEEKLY,
    limit: int = Query(20, ge=1, le=100),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    
    # Calculate period boundaries
    if period == LeaderboardPeriod.DAILY:
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == LeaderboardPeriod.WEEKLY:
        # Start of week (Monday)
        days_since_monday = now.weekday()
        period_start = (now.replace(hour=0, minute=0, second=0, microsecond=0)
                       .replace(day=now.day - days_since_monday))
        # End of week (Sunday)
        period_end = period_start.replace(day=period_start.day + 6,
                                         hour=23, minute=59, second=59)
    elif period == LeaderboardPeriod.MONTHLY:
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Last day of month
        if now.month == 12:
            period_end = now.replace(year=now.year + 1, month=1, day=1,
                                    hour=0, minute=0, second=0) - timezone.utc
        else:
            period_end = now.replace(month=now.month + 1, day=1,
                                    hour=0, minute=0, second=0) - timezone.utc
    else:  # ALL_TIME
        period_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        period_end = now
    
    # Get tasks completed in this period
    query = db.query(
        Task.assigned_to_agent_id,
        db.func.count(Task.id).label('tasks_completed'),
        db.func.sum(Task.points).label('total_points'),
    ).filter(
        Task.status == TaskStatus.COMPLETED,
        Task.completed_at >= period_start,
        Task.completed_at <= period_end,
    ).group_by(Task.assigned_to_agent_id)
    
    results = query.all()
    
    # Build response with rankings
    leaderboard_entries = []
    for rank, row in enumerate(sorted(results, key=lambda x: x.total_points or 0, reverse=True), 1):
        leaderboard_entries.append({
            "rank": rank,
            "agent_id": row.assigned_to_agent_id,
            "tasks_completed": row.tasks_completed,
            "total_points": row.total_points or 0,
            "period": period.value,
            "period_start": period_start,
            "period_end": period_end,
        })
    
    return {
        "period": period.value,
        "entries": leaderboard_entries[:limit],
    }


@router.get("/my-rank")
def get_my_rank(
    period: LeaderboardPeriod = LeaderboardPeriod.WEEKLY,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    
    # Calculate period boundaries (same logic as above)
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
    else:
        period_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        period_end = now
    
    # Get my stats
    my_tasks = db.query(
        db.func.count(Task.id).label('tasks_completed'),
        db.func.sum(Task.points).label('total_points'),
    ).filter(
        Task.assigned_to_agent_id == agent_id,
        Task.status == TaskStatus.COMPLETED,
        Task.completed_at >= period_start,
        Task.completed_at <= period_end,
    ).first()
    
    my_points = my_tasks.total_points or 0
    my_tasks_count = my_tasks.tasks_completed or 0
    
    # Calculate rank
    higher_count = db.query(db.func.count()).filter(
        Task.assigned_to_agent_id != agent_id,
        Task.status == TaskStatus.COMPLETED,
        Task.completed_at >= period_start,
        Task.completed_at <= period_end,
        Task.points > my_points,
    ).scalar()
    
    my_rank = higher_count + 1
    
    # Get average rating for my completed tasks
    avg_rating = db.query(db.func.avg(TaskRating.score)).filter(
        TaskRating.rated_agent_id == agent_id,
    ).scalar()
    
    return {
        "agent_id": agent_id,
        "rank": my_rank,
        "tasks_completed": my_tasks_count,
        "total_points": my_points,
        "avg_rating": round(avg_rating, 2) if avg_rating else None,
        "period": period.value,
    }


@router.get("/agent/{agent_id}")
def get_agent_stats(
    agent_id: str,
    period: LeaderboardPeriod = LeaderboardPeriod.WEEKLY,
    current_agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    
    # Calculate period boundaries
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
    else:
        period_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
        period_end = now
    
    # Get agent stats
    agent_tasks = db.query(
        db.func.count(Task.id).label('tasks_completed'),
        db.func.sum(Task.points).label('total_points'),
    ).filter(
        Task.assigned_to_agent_id == agent_id,
        Task.status == TaskStatus.COMPLETED,
        Task.completed_at >= period_start,
        Task.completed_at <= period_end,
    ).first()
    
    avg_rating = db.query(db.func.avg(TaskRating.score)).filter(
        TaskRating.rated_agent_id == agent_id,
    ).scalar()
    
    return {
        "agent_id": agent_id,
        "tasks_completed": agent_tasks.tasks_completed or 0,
        "total_points": agent_tasks.total_points or 0,
        "avg_rating": round(avg_rating, 2) if avg_rating else None,
        "period": period.value,
    }
