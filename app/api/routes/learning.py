from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.api.schemas.learning import LearningSubmit, LearningRecordResponse
from app.services.learning_service import LearningService

router = APIRouter(tags=["learning"])


@router.post("/posts/{post_id}/learn")
def submit_learning(
    post_id: str,
    data: LearningSubmit,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = LearningService(db)
    record = svc.submit_learning(agent_id, post_id, data)
    return {"message": "Learning recorded", "record_id": record.id, "status": record.status.value}


@router.get("/my/learning-records")
def my_learning_records(
    status_filter: Optional[str] = Query(None, alias="status"),
    only_outdated: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = LearningService(db)
    records, total = svc.get_my_records(
        agent_id, status=status_filter, only_outdated=only_outdated, page=page, size=size
    )
    return {"items": records, "total": total, "page": page, "size": size}
