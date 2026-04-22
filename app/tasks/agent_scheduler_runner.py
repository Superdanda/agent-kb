import logging
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.repositories.agent_scheduler_repo import AgentSchedulerRepository
from app.models.agent_scheduler import SchedulerStatus

logger = logging.getLogger(__name__)


def execute_due_schedulers():
    """
    Poll for due schedulers and execute them.
    This function is called every minute by the BackgroundScheduler.
    Each due scheduler is executed in-process (for simplicity).
    For heavy workloads, consider offloading to a worker queue.
    """
    db = SessionLocal()
    try:
        repo = AgentSchedulerRepository(db)
        due_schedulers = repo.get_due_tasks(limit=50)

        if not due_schedulers:
            logger.debug("No due schedulers found")
            return

        logger.info(f"Found {len(due_schedulers)} due schedulers")
        for scheduler in due_schedulers:
            _execute_scheduler(db, repo, scheduler)

    except Exception as e:
        logger.error(f"Error polling due schedulers: {e}")
        raise
    finally:
        db.close()


def _execute_scheduler(db, repo, scheduler):
    """Execute a single scheduler task."""
    started_at = datetime.now(timezone.utc)

    # Mark as RUNNING
    repo.update_status(
        scheduler.id,
        status=SchedulerStatus.RUNNING.value,
        last_run_at=started_at,
    )

    log = None
    try:
        logger.info(f"Executing scheduler {scheduler.id} ({scheduler.task_name})")

        # Build a context dict for the task
        context = {
            "scheduler_id": scheduler.id,
            "agent_id": scheduler.agent_id,
            "task_name": scheduler.task_name,
            "task_type": scheduler.task_type,
        }

        # Execute based on task_name pattern
        result = _dispatch_task(scheduler.task_name, scheduler.task_type, context)

        # Mark as SUCCESS
        finished_at = datetime.now(timezone.utc)
        status = SchedulerStatus.SUCCESS.value
        repo.update_status(
            scheduler.id,
            status=status,
            result=f"Success: {result}" if result else "Success",
            last_run_at=started_at,
        )
        log = repo.create_execution_log(
            scheduler_id=scheduler.id,
            started_at=started_at,
            status=status,
            result=result,
        )
        repo.finish_execution_log(log.id, finished_at, status, result)
        logger.info(f"Scheduler {scheduler.id} completed successfully")

    except Exception as e:
        finished_at = datetime.now(timezone.utc)
        error_msg = str(e)
        logger.error(f"Scheduler {scheduler.id} failed: {error_msg}")

        repo.update_status(
            scheduler.id,
            status=SchedulerStatus.FAILED.value,
            result=f"Error: {error_msg}",
        )
        log = repo.create_execution_log(
            scheduler_id=scheduler.id,
            started_at=started_at,
            status=SchedulerStatus.FAILED.value,
            result=error_msg,
        )
        repo.finish_execution_log(log.id, finished_at, SchedulerStatus.FAILED.value, error_msg)


def _dispatch_task(task_name: str, task_type: str, context: dict) -> str:
    """
    Dispatch a task by name.
    Extend this function to register more task handlers.
    Currently logs the task; replace with actual execution logic.
    """
    # Placeholder: In a real system, you would look up registered handlers
    # e.g., registered_tasks = {"sync_posts": sync_posts_task, "push_metrics": push_metrics_task}
    # handler = registered_tasks.get(task_name)
    # if handler:
    #     return handler(context)
    logger.info(f"Dispatching task '{task_name}' (type={task_type}) with context: {context}")
    return f"Task '{task_name}' dispatched (no-op in placeholder)"
