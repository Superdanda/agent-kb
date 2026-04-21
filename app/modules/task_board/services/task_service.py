import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.modules.task_board.models.task import Task, TaskStatus, TaskPriority, TaskDifficulty
from app.modules.task_board.models.task_status_log import TaskStatusLog
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        title: str,
        created_by_agent_id: str,
        description: Optional[str] = None,
        assigned_to_agent_id: Optional[str] = None,
        domain_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        difficulty: Optional[TaskDifficulty] = None,
        points: int = 0,
        estimated_hours: Optional[int] = None,
        due_date=None,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Task:
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            created_by_agent_id=created_by_agent_id,
            assigned_to_agent_id=assigned_to_agent_id,
            domain_id=domain_id,
            priority=priority,
            difficulty=difficulty,
            points=points,
            estimated_hours=estimated_hours,
            due_date=due_date,
            tags_json=tags or [],
            metadata_json=metadata or {},
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        self._log_status_change(task.id, created_by_agent_id, None, TaskStatus.PENDING)

        return task

    def get_task(self, task_id: str) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        return task

    def update_task(
        self,
        task_id: str,
        agent_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        assigned_to_agent_id: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        difficulty: Optional[TaskDifficulty] = None,
        points: Optional[int] = None,
        estimated_hours: Optional[int] = None,
        due_date=None,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Task:
        task = self.get_task(task_id)

        if task.created_by_agent_id != agent_id and task.assigned_to_agent_id != agent_id:
            raise PermissionDeniedError("Only the creator or assignee can update the task")

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if assigned_to_agent_id is not None:
            task.assigned_to_agent_id = assigned_to_agent_id
        if priority is not None:
            task.priority = priority
        if difficulty is not None:
            task.difficulty = difficulty
        if points is not None:
            task.points = points
        if estimated_hours is not None:
            task.estimated_hours = estimated_hours
        if due_date is not None:
            task.due_date = due_date
        if tags is not None:
            task.tags_json = tags
        if metadata is not None:
            task.metadata_json = metadata

        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_task_status(
        self,
        task_id: str,
        agent_id: str,
        new_status: TaskStatus,
        change_reason: Optional[str] = None,
    ) -> Task:
        task = self.get_task(task_id)

        if task.assigned_to_agent_id != agent_id and task.created_by_agent_id != agent_id:
            raise PermissionDeniedError("Only the creator or assignee can change task status")

        old_status = task.status
        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)

        if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.now(timezone.utc)
        if new_status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now(timezone.utc)
            if task.actual_hours is None and task.started_at:
                delta = datetime.now(timezone.utc) - task.started_at
                task.actual_hours = int(delta.total_seconds() / 3600)

        self.db.commit()
        self.db.refresh(task)

        self._log_status_change(task.id, agent_id, old_status, new_status, change_reason)

        return task

    def get_tasks(
        self,
        created_by_agent_id: Optional[str] = None,
        assigned_to_agent_id: Optional[str] = None,
        domain_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Task], int]:
        query = self.db.query(Task)

        if created_by_agent_id:
            query = query.filter(Task.created_by_agent_id == created_by_agent_id)
        if assigned_to_agent_id:
            query = query.filter(Task.assigned_to_agent_id == assigned_to_agent_id)
        if domain_id:
            query = query.filter(Task.domain_id == domain_id)
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)

        total = query.count()
        offset = (page - 1) * size
        tasks = query.order_by(desc(Task.created_at)).offset(offset).limit(size).all()
        return tasks, total

    def get_my_tasks(
        self,
        agent_id: str,
        role: str = "assignee",
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Task], int]:
        if role == "creator":
            return self.get_tasks(created_by_agent_id=agent_id, page=page, size=size)
        return self.get_tasks(assigned_to_agent_id=agent_id, page=page, size=size)

    def delete_task(self, task_id: str, agent_id: str) -> bool:
        task = self.get_task(task_id)
        if task.created_by_agent_id != agent_id:
            raise PermissionDeniedError("Only the creator can delete the task")
        self.db.delete(task)
        self.db.commit()
        return True

    def get_task_status_logs(self, task_id: str) -> List[TaskStatusLog]:
        task = self.get_task(task_id)
        return task.status_logs.all()

    def _log_status_change(
        self,
        task_id: str,
        agent_id: str,
        from_status: Optional[TaskStatus],
        to_status: TaskStatus,
        change_reason: Optional[str] = None,
    ) -> TaskStatusLog:
        log = TaskStatusLog(
            id=str(uuid.uuid4()),
            task_id=task_id,
            agent_id=agent_id,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value,
            change_reason=change_reason,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
