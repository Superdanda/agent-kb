import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent, get_current_admin_or_agent
from app.modules.task_board.models.task import Task, TaskPriority, TaskDifficulty, TaskStatus
from app.modules.task_board.models.task_status_log import TaskStatusLog
from app.modules.task_board.models.task_rating import TaskRating, RatingDimension
from app.repositories.agent_repo import AgentRepository
from app.modules.task_board.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.modules.task_board.schemas.task_status_log import TaskStatusLogResponse
from app.modules.task_board.schemas.task_rating import TaskRatingCreate, TaskRatingResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_agent_name(db: Session, agent_id: str) -> str:
    agent = AgentRepository(db).get_by_id(agent_id)
    return agent.name if agent else agent_id


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(
    title: str,
    description: Optional[str] = None,
    priority: TaskPriority = TaskPriority.MEDIUM,
    difficulty: Optional[TaskDifficulty] = None,
    assigned_to_agent_id: Optional[str] = None,
    domain_id: Optional[str] = None,
    points: int = 0,
    estimated_hours: Optional[int] = None,
    due_date: Optional[datetime] = None,
    tags: Optional[List[str]] = None,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    task = Task(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        created_by_agent_id=agent_id,
        assigned_to_agent_id=assigned_to_agent_id,
        domain_id=domain_id,
        priority=priority,
        difficulty=difficulty,
        status=TaskStatus.PENDING,
        points=points,
        estimated_hours=estimated_hours,
        due_date=due_date,
        tags_json=tags or [],
    )
    db.add(task)
    
    # Log task creation
    status_log = TaskStatusLog(
        id=str(uuid.uuid4()),
        task_id=task.id,
        agent_id=agent_id,
        from_status=None,
        to_status=TaskStatus.PENDING.value,
        change_reason="Task created",
    )
    db.add(status_log)
    db.commit()
    db.refresh(task)
    
    return TaskResponse.model_validate(task)


@router.get("")
def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
    domain_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _actor: dict = Depends(get_current_admin_or_agent),
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    
    if status_filter:
        query = query.filter(Task.status == TaskStatus(status_filter))
    if priority:
        query = query.filter(Task.priority == TaskPriority(priority))
    if assigned_to:
        query = query.filter(Task.assigned_to_agent_id == assigned_to)
    if created_by:
        query = query.filter(Task.created_by_agent_id == created_by)
    if domain_id:
        query = query.filter(Task.domain_id == domain_id)
    
    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return {"items": [TaskResponse.model_validate(t) for t in tasks], "total": total, "page": page, "size": size}


@router.get("/{task_id}")
def get_task(
    task_id: str,
    _actor: dict = Depends(get_current_admin_or_agent),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Task {task_id} not found")
    
    # Attach agent names
    task.created_by_name = get_agent_name(db, task.created_by_agent_id)
    if task.assigned_to_agent_id:
        task.assigned_to_name = get_agent_name(db, task.assigned_to_agent_id)
    
    return TaskResponse.model_validate(task)


@router.put("/{task_id}")
def update_task(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[TaskPriority] = None,
    difficulty: Optional[TaskDifficulty] = None,
    assigned_to_agent_id: Optional[str] = None,
    domain_id: Optional[str] = None,
    points: Optional[int] = None,
    estimated_hours: Optional[int] = None,
    due_date: Optional[datetime] = None,
    tags: Optional[List[str]] = None,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Task {task_id} not found")
    
    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if priority is not None:
        task.priority = priority
    if difficulty is not None:
        task.difficulty = difficulty
    if assigned_to_agent_id is not None:
        task.assigned_to_agent_id = assigned_to_agent_id
    if domain_id is not None:
        task.domain_id = domain_id
    if points is not None:
        task.points = points
    if estimated_hours is not None:
        task.estimated_hours = estimated_hours
    if due_date is not None:
        task.due_date = due_date
    if tags is not None:
        task.tags_json = tags
    
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/status")
def update_task_status(
    task_id: str,
    new_status: TaskStatus,
    change_reason: Optional[str] = None,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Task {task_id} not found")
    
    old_status = task.status
    
    # Log status change
    status_log = TaskStatusLog(
        id=str(uuid.uuid4()),
        task_id=task.id,
        agent_id=agent_id,
        from_status=old_status.value if old_status else None,
        to_status=new_status.value,
        change_reason=change_reason,
    )
    db.add(status_log)
    
    task.status = new_status
    
    # Update timestamps based on status
    now = datetime.now(timezone.utc)
    if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
        task.started_at = now
    elif new_status == TaskStatus.COMPLETED:
        task.completed_at = now
    
    task.updated_at = now
    db.commit()
    db.refresh(task)
    
    return TaskResponse.model_validate(task)


@router.get("/{task_id}/logs")
def get_task_status_logs(
    task_id: str,
    _actor: dict = Depends(get_current_admin_or_agent),
    db: Session = Depends(get_db),
):
    logs = db.query(TaskStatusLog).filter(TaskStatusLog.task_id == task_id).order_by(TaskStatusLog.created_at).all()
    return [TaskStatusLogResponse.model_validate(log) for log in logs]


@router.post("/{task_id}/rate")
def rate_task(
    task_id: str,
    rated_agent_id: str,
    dimension: RatingDimension,
    score: int = Query(..., ge=1, le=5),
    comment: Optional[str] = None,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Task {task_id} not found")
    
    # Check if rating already exists
    existing = db.query(TaskRating).filter(
        TaskRating.task_id == task_id,
        TaskRating.rater_agent_id == agent_id,
        TaskRating.rated_agent_id == rated_agent_id,
        TaskRating.dimension == dimension.value,
    ).first()
    
    if existing:
        existing.score = score
        existing.comment = comment
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return TaskRatingResponse.model_validate(existing)
    
    rating = TaskRating(
        id=str(uuid.uuid4()),
        task_id=task_id,
        rater_agent_id=agent_id,
        rated_agent_id=rated_agent_id,
        dimension=dimension.value,
        score=score,
        comment=comment,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    
    return TaskRatingResponse.model_validate(rating)


@router.get("/{task_id}/ratings")
def get_task_ratings(
    task_id: str,
    _actor: dict = Depends(get_current_admin_or_agent),
    db: Session = Depends(get_db),
):
    ratings = db.query(TaskRating).filter(TaskRating.task_id == task_id).all()
    return [TaskRatingResponse.model_validate(r) for r in ratings]


@router.get("/my/tasks")
def my_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    query = db.query(Task).filter(
        (Task.assigned_to_agent_id == agent_id) | (Task.created_by_agent_id == agent_id)
    )
    
    if status_filter:
        query = query.filter(Task.status == TaskStatus(status_filter))
    
    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return {"items": [TaskResponse.model_validate(t) for t in tasks], "total": total, "page": page, "size": size}
