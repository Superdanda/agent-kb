import logging

from app.core.database import SessionLocal
from app.modules.task_board.services.task_service import TaskService

logger = logging.getLogger(__name__)


def run_task_lease_recovery() -> None:
    db = SessionLocal()
    try:
        recovered = TaskService(db).recover_expired_leases(limit=100)
        if recovered:
            logger.info("Recovered %s expired task lease(s)", recovered)
        else:
            logger.debug("Task lease recovery: no expired leases")
    except Exception as exc:
        db.rollback()
        logger.error("Task lease recovery error: %s", exc)
    finally:
        db.close()
