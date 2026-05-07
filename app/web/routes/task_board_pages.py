import uuid
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.modules.task_board.models.task import Task, TaskStatus, TaskPriority, TaskDifficulty
from app.modules.task_board.models.task_material import TaskMaterial
from app.modules.task_board.models.task_status_log import TaskStatusLog
from app.modules.task_board.models.leaderboard import Leaderboard, LeaderboardPeriod
from app.repositories.agent_repo import AgentRepository
from app.web import templates

router = APIRouter(prefix="/tasks", tags=["task_board_pages"])

def get_agent_name(db, agent_id):
    agent = AgentRepository(db).get_by_id(agent_id)
    return agent.name if agent else agent_id

@router.get("/tasks", response_class=HTMLResponse)
async def task_list(
    request: Request,
    status_filter: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1),
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if priority:
        query = query.filter(Task.priority == priority)
    
    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    
    # Attach agent names
    for task in tasks:
        task.created_by_name = get_agent_name(db, task.created_by_agent_id)
        if task.assigned_to_agent_id:
            task.assigned_to_name = get_agent_name(db, task.assigned_to_agent_id)
    
    return templates.TemplateResponse("task_board/list.html", {
        "request": request,
        "tasks": tasks,
        "total": total,
        "page": page,
        "status_filter": status_filter,
        "priority": priority,
        "status_options": [s.value for s in TaskStatus],
        "priority_options": [p.value for p in TaskPriority],
    })

@router.get("/tasks/new", response_class=HTMLResponse)
async def new_task_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("task_board/create.html", {
        "request": request,
        "priority_options": [p.value for p in TaskPriority],
        "difficulty_options": [d.value for d in TaskDifficulty],
    })

@router.post("/tasks/new")
async def create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form("MEDIUM"),
    difficulty: str = Form(None),
    points: int = Form(0),
    estimated_hours: int = Form(None),
    due_date: str = Form(None),
    agent_id: str = Form(...),
    db: Session = Depends(get_db),
):
    task = Task(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        created_by_agent_id=agent_id,
        priority=TaskPriority(priority),
        difficulty=TaskDifficulty(difficulty) if difficulty else None,
        points=points,
        estimated_hours=estimated_hours,
        due_date=due_date if due_date else None,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    
    log = TaskStatusLog(
        id=str(uuid.uuid4()),
        task_id=task.id,
        agent_id=agent_id,
        from_status=None,
        to_status=TaskStatus.PENDING.value,
        change_reason="Task created",
    )
    db.add(log)
    db.commit()
    
    return RedirectResponse(url=f"/tasks/{task.id}", status_code=303)

@router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return HTMLResponse("Task not found", status_code=404)
    
    task.created_by_name = get_agent_name(db, task.created_by_agent_id)
    if task.assigned_to_agent_id:
        task.assigned_to_name = get_agent_name(db, task.assigned_to_agent_id)
    
    logs = db.query(TaskStatusLog).filter(TaskStatusLog.task_id == task_id).order_by(TaskStatusLog.created_at).all()
    materials = db.query(TaskMaterial).filter(TaskMaterial.task_id == task_id).order_by(TaskMaterial.order_index).all()
    
    return templates.TemplateResponse("task_board/detail.html", {
        "request": request,
        "task": task,
        "logs": logs,
        "materials": materials,
        "status_options": [s.value for s in TaskStatus],
    })

@router.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
async def edit_task_page(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return HTMLResponse("Task not found", status_code=404)
    
    return templates.TemplateResponse("task_board/edit.html", {
        "request": request,
        "task": task,
        "priority_options": [p.value for p in TaskPriority],
        "difficulty_options": [d.value for d in TaskDifficulty],
        "status_options": [s.value for s in TaskStatus],
    })

@router.post("/tasks/{task_id}/edit")
async def update_task(
    request: Request,
    task_id: str,
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form(...),
    difficulty: str = Form(None),
    points: int = Form(0),
    estimated_hours: int = Form(None),
    due_date: str = Form(None),
    agent_id: str = Form(...),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return HTMLResponse("Task not found", status_code=404)
    
    task.title = title
    task.description = description
    task.priority = TaskPriority(priority)
    task.difficulty = TaskDifficulty(difficulty) if difficulty else None
    task.points = points
    task.estimated_hours = estimated_hours
    task.due_date = due_date if due_date else None
    db.commit()
    
    return RedirectResponse(url=f"/tasks/{task.id}", status_code=303)

@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(
    request: Request,
    period: str = Query("WEEKLY"),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone
    
    period_enum = LeaderboardPeriod(period)
    now = datetime.now(timezone.utc)
    
    # Calculate period boundaries
    if period_enum == LeaderboardPeriod.DAILY:
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period_enum == LeaderboardPeriod.WEEKLY:
        days_since_monday = now.weekday()
        period_start = (now.replace(hour=0, minute=0, second=0, microsecond=0)
                       .replace(day=now.day - days_since_monday))
        period_end = period_start.replace(day=period_start.day + 6,
                                         hour=23, minute=59, second=59)
    elif period_enum == LeaderboardPeriod.MONTHLY:
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
    
    # Get leaderboard data
    from sqlalchemy import func
    results = db.query(
        Task.assigned_to_agent_id,
        func.count(Task.id).label('tasks_completed'),
        func.sum(Task.points).label('total_points'),
    ).filter(
        Task.status.in_([TaskStatus.COMPLETED, TaskStatus.CONFIRMED]),
        Task.completed_at >= period_start,
        Task.completed_at <= period_end,
    ).group_by(Task.assigned_to_agent_id).all()
    
    entries = []
    for rank, row in enumerate(sorted(results, key=lambda x: x.total_points or 0, reverse=True), 1):
        agent_name = get_agent_name(db, row.assigned_to_agent_id)
        entries.append({
            "rank": rank,
            "agent_id": row.assigned_to_agent_id,
            "agent_name": agent_name,
            "tasks_completed": row.tasks_completed,
            "total_points": row.total_points or 0,
        })
    
    return templates.TemplateResponse("task_board/leaderboard.html", {
        "request": request,
        "entries": entries,
        "period": period,
        "period_options": [p.value for p in LeaderboardPeriod],
    })
