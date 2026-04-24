"""Scheduler dispatch handlers.

This module turns due `AgentScheduler` rows into concrete platform work. The
initial MVP dispatches to the existing task board so agents can poll the work
through `/api/agent/tasks/pending` or `/api/tasks` without adding a new queue
schema.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.models.agent import Agent, AgentStatus
from app.models.agent_scheduler import AgentScheduler
from app.modules.task_board.models.task import TaskPriority
from app.modules.task_board.services.task_service import TaskService


@dataclass(frozen=True)
class SchedulerDispatchResult:
    status: str
    message: str
    task_id: str | None = None


class SchedulerDispatchHandler(Protocol):
    def dispatch(self, db: Session, scheduler: AgentScheduler, context: dict) -> SchedulerDispatchResult:
        ...


class TaskBoardDispatchHandler:
    """Create a task-board item assigned to the scheduler owner Agent."""

    def dispatch(self, db: Session, scheduler: AgentScheduler, context: dict) -> SchedulerDispatchResult:
        agent = db.query(Agent).filter(Agent.id == scheduler.agent_id).first()
        if not agent:
            raise ResourceNotFoundError(f"Agent {scheduler.agent_id} not found")
        if agent.status != AgentStatus.ACTIVE:
            raise ValidationError(f"agent_offline: Agent {scheduler.agent_id} is not ACTIVE")

        title = self._normalize_title(scheduler.task_name)
        metadata = {
            "source": "agent_scheduler",
            "scheduler_id": scheduler.id,
            "scheduler_task_name": scheduler.task_name,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
        }
        task = TaskService(db).create_task(
            title=title,
            description=f"Auto-dispatched by scheduler {scheduler.id}",
            created_by_agent_id=scheduler.agent_id,
            assigned_to_agent_id=scheduler.agent_id,
            priority=TaskPriority.MEDIUM,
            metadata=metadata,
        )
        return SchedulerDispatchResult(
            status="queued",
            message=f"Created task {task.id} for agent {scheduler.agent_id}",
            task_id=task.id,
        )

    def _normalize_title(self, task_name: str) -> str:
        for prefix in ("task:", "create_task:", "agent_pending_queue:"):
            if task_name.startswith(prefix):
                value = task_name[len(prefix):].strip()
                if value:
                    return value
        return f"Scheduled task: {task_name}"


_DEFAULT_HANDLER = TaskBoardDispatchHandler()
_HANDLER_REGISTRY: dict[str, SchedulerDispatchHandler] = {
    "task": _DEFAULT_HANDLER,
    "create_task": _DEFAULT_HANDLER,
    "agent_pending_queue": _DEFAULT_HANDLER,
}


def resolve_dispatch_handler(task_name: str) -> SchedulerDispatchHandler:
    command = task_name.split(":", 1)[0].strip() if task_name else ""
    return _HANDLER_REGISTRY.get(command, _DEFAULT_HANDLER)


def dispatch_scheduler(db: Session, scheduler: AgentScheduler, context: dict) -> SchedulerDispatchResult:
    handler = resolve_dispatch_handler(scheduler.task_name)
    return handler.dispatch(db, scheduler, context)
