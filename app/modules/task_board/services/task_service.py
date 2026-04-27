import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.modules.task_board.models.task import Task, TaskStatus, TaskPriority, TaskDifficulty
from app.modules.task_board.models.task_status_log import TaskStatusLog
from app.modules.task_board.models.task_submission_receipt import TaskSubmissionReceipt
from app.modules.task_board.services.task_state_machine import (
    TaskAction,
    assert_transition_allowed,
    target_status_for,
)
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError, ValidationError
from app.models.agent_activity_log import AgentActivityLog


DEFAULT_TASK_LEASE_SECONDS = 30 * 60


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        title: str,
        created_by_agent_id: Optional[str] = None,
        created_by_admin_uuid: Optional[str] = None,
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
        if not title or not title.strip():
            raise ValidationError("Task title is required")

        task = Task(
            id=str(uuid.uuid4()),
            title=title.strip(),
            description=description,
            created_by_agent_id=created_by_agent_id,
            created_by_admin_uuid=created_by_admin_uuid,
            assigned_to_agent_id=assigned_to_agent_id,
            domain_id=domain_id,
            priority=priority,
            difficulty=difficulty,
            status=TaskStatus.PENDING if assigned_to_agent_id else TaskStatus.UNCLAIMED,
            points=points,
            estimated_hours=estimated_hours,
            due_date=due_date,
            tags_json=tags or [],
            metadata_json=metadata or {},
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        if created_by_admin_uuid:
            self._log_status_change(
                task.id,
                None,
                None,
                task.status,
                change_reason="Task created",
                admin_uuid=created_by_admin_uuid,
            )
        else:
            self._log_status_change(
                task.id,
                created_by_agent_id,
                None,
                task.status,
                change_reason="Task created",
            )

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
        domain_id: Optional[str] = None,
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
            if not title.strip():
                raise ValidationError("Task title is required")
            task.title = title.strip()
        if description is not None:
            task.description = description
        if assigned_to_agent_id is not None:
            task.assigned_to_agent_id = assigned_to_agent_id
        if domain_id is not None:
            task.domain_id = domain_id
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
        if new_status in {TaskStatus.CONFIRMED, TaskStatus.COMPLETED}:
            task.completed_at = datetime.now(timezone.utc)
            if task.actual_hours is None and task.started_at:
                delta = datetime.now(timezone.utc) - task.started_at
                task.actual_hours = int(delta.total_seconds() / 3600)

        self.db.commit()
        self.db.refresh(task)

        self._log_status_change(task.id, agent_id, old_status, new_status, change_reason)

        return task

    def claim_task(self, task_id: str, agent_id: str) -> Task:
        task = (
            self.db.query(Task)
            .filter(Task.id == task_id)
            .with_for_update()
            .first()
        )
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        if task.assigned_to_agent_id and task.assigned_to_agent_id != agent_id:
            raise PermissionDeniedError("Task is assigned to another agent")

        assert_transition_allowed(task.status, TaskAction.CLAIM)
        now = datetime.now(timezone.utc)
        old_status = task.status
        task.assigned_to_agent_id = agent_id
        task.status = target_status_for(TaskAction.CLAIM)
        task.started_at = now
        task.lease_token = secrets.token_urlsafe(32)
        task.lease_renewed_at = now
        task.lease_expires_at = now + timedelta(seconds=DEFAULT_TASK_LEASE_SECONDS)
        task.updated_at = now
        self.db.commit()
        self.db.refresh(task)
        self._log_status_change(task.id, agent_id, old_status, task.status, "Task claimed")
        self._log_activity(
            agent_id=agent_id,
            action="task.claim",
            object_type="task",
            object_id=task.id,
            status="SUCCESS",
            detail={
                "from_status": old_status.value if old_status else None,
                "to_status": task.status.value,
                "lease_expires_at": task.lease_expires_at.isoformat() if task.lease_expires_at else None,
            },
        )
        return task

    def submit_task_result(
        self,
        task_id: str,
        agent_id: str,
        result_summary: str,
        actual_hours: Optional[int] = None,
        lease_token: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        require_lease: bool = False,
    ) -> Task:
        task = (
            self.db.query(Task)
            .filter(Task.id == task_id)
            .with_for_update()
            .first()
        )
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        self._ensure_assignee(task, agent_id)
        if not result_summary or not result_summary.strip():
            raise ValidationError("result_summary is required")

        if idempotency_key:
            existing_receipt = (
                self.db.query(TaskSubmissionReceipt)
                .filter(
                    TaskSubmissionReceipt.task_id == task_id,
                    TaskSubmissionReceipt.agent_id == agent_id,
                    TaskSubmissionReceipt.idempotency_key == idempotency_key,
                )
                .first()
            )
            if existing_receipt:
                self._log_activity(
                    agent_id=agent_id,
                    action="task.submit",
                    object_type="task",
                    object_id=task.id,
                    status="IDEMPOTENT_REPLAY",
                    detail={"idempotency_key": idempotency_key},
                )
                return task

        if require_lease:
            if not lease_token:
                raise ValidationError("lease_token is required")
            if not idempotency_key:
                raise ValidationError("idempotency_key is required")
            self._ensure_active_lease(task, lease_token)

        assert_transition_allowed(task.status, TaskAction.SUBMIT)
        old_status = task.status
        task.status = target_status_for(TaskAction.SUBMIT)
        task.actual_hours = actual_hours
        task.updated_at = datetime.now(timezone.utc)
        task.lease_token = None
        task.lease_expires_at = None
        task.lease_renewed_at = None
        metadata = task.metadata_json or {}
        metadata["result_summary"] = result_summary.strip()
        metadata["submitted_at"] = datetime.now(timezone.utc).isoformat()
        task.metadata_json = metadata
        if idempotency_key:
            self.db.add(
                TaskSubmissionReceipt(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    agent_id=agent_id,
                    idempotency_key=idempotency_key,
                    result_summary=result_summary.strip(),
                    status=target_status_for(TaskAction.SUBMIT).value,
                )
            )
        self.db.commit()
        self.db.refresh(task)
        self._log_status_change(task.id, agent_id, old_status, task.status, "Task submitted")
        self._log_activity(
            agent_id=agent_id,
            action="task.submit",
            object_type="task",
            object_id=task.id,
            status="SUCCESS",
            detail={
                "from_status": old_status.value if old_status else None,
                "to_status": task.status.value,
                "idempotency_key": idempotency_key,
            },
        )
        return task

    def abandon_task(
        self,
        task_id: str,
        agent_id: str,
        reason: Optional[str] = None,
        lease_token: Optional[str] = None,
        require_lease: bool = False,
    ) -> Task:
        task = self.get_task(task_id)
        self._ensure_assignee(task, agent_id)
        if require_lease:
            if not lease_token:
                raise ValidationError("lease_token is required")
            self._ensure_active_lease(task, lease_token)
        assert_transition_allowed(task.status, TaskAction.ABANDON)

        old_status = task.status
        task.status = target_status_for(TaskAction.ABANDON)
        task.assigned_to_agent_id = None
        task.lease_token = None
        task.lease_expires_at = None
        task.lease_renewed_at = None
        task.updated_at = datetime.now(timezone.utc)
        metadata = task.metadata_json or {}
        if reason:
            metadata["abandon_reason"] = reason.strip()
        metadata["abandoned_at"] = datetime.now(timezone.utc).isoformat()
        task.metadata_json = metadata
        self.db.commit()
        self.db.refresh(task)
        self._log_status_change(task.id, agent_id, old_status, task.status, reason or "Task abandoned")
        self._log_activity(
            agent_id=agent_id,
            action="task.abandon",
            object_type="task",
            object_id=task.id,
            status="SUCCESS",
            detail={"reason": reason, "from_status": old_status.value if old_status else None},
        )
        return task

    def confirm_task(
        self,
        task_id: str,
        reviewer_agent_id: Optional[str] = None,
        reviewer_admin_uuid: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Task:
        task = self.get_task(task_id)
        self._ensure_reviewer(task, reviewer_agent_id, reviewer_admin_uuid)
        assert_transition_allowed(task.status, TaskAction.CONFIRM)

        old_status = task.status
        task.status = target_status_for(TaskAction.CONFIRM)
        task.completed_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        self._log_status_change(
            task.id,
            reviewer_agent_id,
            old_status,
            task.status,
            reason or "Task confirmed",
            admin_uuid=reviewer_admin_uuid,
        )

        try:
            from app.modules.task_board.services.leaderboard_service import LeaderboardService

            LeaderboardService(self.db).update_on_task_complete(task.id)
            self.db.refresh(task)
        except Exception:
            # Leaderboard updates are derived data; do not roll back the task state.
            pass

        return task

    def reject_task(
        self,
        task_id: str,
        reviewer_agent_id: Optional[str] = None,
        reviewer_admin_uuid: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Task:
        task = self.get_task(task_id)
        self._ensure_reviewer(task, reviewer_agent_id, reviewer_admin_uuid)
        if not reason or not reason.strip():
            raise ValidationError("reject reason is required")
        assert_transition_allowed(task.status, TaskAction.REJECT)

        old_status = task.status
        task.status = target_status_for(TaskAction.REJECT)
        task.updated_at = datetime.now(timezone.utc)
        metadata = task.metadata_json or {}
        metadata["reject_reason"] = reason.strip()
        metadata["rejected_at"] = datetime.now(timezone.utc).isoformat()
        task.metadata_json = metadata
        self.db.commit()
        self.db.refresh(task)
        self._log_status_change(
            task.id,
            reviewer_agent_id,
            old_status,
            task.status,
            reason.strip(),
            admin_uuid=reviewer_admin_uuid,
        )
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

    def list_available_tasks(
        self,
        agent_id: str,
        statuses: Optional[List[TaskStatus]] = None,
        limit: int = 10,
    ) -> List[Task]:
        status_values = statuses or [TaskStatus.PENDING, TaskStatus.UNCLAIMED]
        return (
            self.db.query(Task)
            .filter(
                ((Task.assigned_to_agent_id == agent_id) | (Task.assigned_to_agent_id.is_(None))),
                Task.status.in_(status_values),
            )
            .order_by(Task.priority.desc(), Task.created_at.asc())
            .limit(limit)
            .all()
        )

    def recover_expired_leases(self, limit: int = 100) -> int:
        now = datetime.now(timezone.utc)
        tasks = (
            self.db.query(Task)
            .filter(
                Task.status == TaskStatus.IN_PROGRESS,
                Task.lease_expires_at.isnot(None),
                Task.lease_expires_at < now,
            )
            .order_by(Task.lease_expires_at.asc())
            .limit(limit)
            .all()
        )
        recovered = 0
        for task in tasks:
            old_status = task.status
            old_agent_id = task.assigned_to_agent_id
            task.status = TaskStatus.UNCLAIMED
            task.assigned_to_agent_id = None
            task.lease_token = None
            task.lease_expires_at = None
            task.lease_renewed_at = None
            task.updated_at = now
            recovered += 1
            self._log_status_change(
                task.id,
                old_agent_id,
                old_status,
                TaskStatus.UNCLAIMED,
                "Task lease expired and was recovered",
            )
            self._log_activity(
                agent_id=old_agent_id,
                action="task.lease_recover",
                object_type="task",
                object_id=task.id,
                status="SUCCESS",
                detail={"expired_at": now.isoformat()},
            )
        if recovered:
            self.db.commit()
        return recovered

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

    def _ensure_assignee(self, task: Task, agent_id: str) -> None:
        if task.assigned_to_agent_id != agent_id:
            raise PermissionDeniedError("Only the assigned agent can operate this task")

    def _ensure_active_lease(self, task: Task, lease_token: str) -> None:
        now = datetime.now(timezone.utc)
        expires_at = task.lease_expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if task.lease_token != lease_token:
            raise PermissionDeniedError("Task lease token does not match")
        if not expires_at or expires_at < now:
            raise PermissionDeniedError("Task lease has expired")

    def _ensure_reviewer(
        self,
        task: Task,
        reviewer_agent_id: Optional[str],
        reviewer_admin_uuid: Optional[str],
    ) -> None:
        if reviewer_admin_uuid:
            return
        if reviewer_agent_id and task.created_by_agent_id == reviewer_agent_id:
            return
        raise PermissionDeniedError("Only the task creator or admin can review this task")

    def _log_status_change(
        self,
        task_id: str,
        agent_id: Optional[str],
        from_status: Optional[TaskStatus],
        to_status: TaskStatus,
        change_reason: Optional[str] = None,
        admin_uuid: Optional[str] = None,
    ) -> TaskStatusLog:
        log = TaskStatusLog(
            id=str(uuid.uuid4()),
            task_id=task_id,
            agent_id=agent_id,
            admin_uuid=admin_uuid,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value,
            change_reason=change_reason,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def _is_valid_agent_uuid(self, uuid_str: str) -> bool:
        """Check if uuid_str exists in agents table"""
        from app.models.agent import Agent
        return self.db.query(Agent).filter(Agent.id == uuid_str).first() is not None

    def _log_activity(
        self,
        agent_id: Optional[str],
        action: str,
        object_type: str,
        object_id: Optional[str],
        status: str,
        detail: Optional[dict] = None,
    ) -> AgentActivityLog:
        log = AgentActivityLog(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            status=status,
            detail_json=detail or {},
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
