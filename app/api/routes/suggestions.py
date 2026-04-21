from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.api.schemas.suggestion import (
    SuggestionCreate,
    SuggestionStatusUpdate,
    SuggestionReplyCreate,
    SuggestionResponse,
    SuggestionReplyResponse,
    LeaderboardEntry,
)
from app.services.suggestion_service import SuggestionService
from app.repositories.agent_repo import AgentRepository

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


def get_agent_name(db: Session, agent_id: str) -> str:
    agent = AgentRepository(db).get_by_id(agent_id)
    return agent.name if agent else agent_id


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SuggestionResponse)
def submit_suggestion(
    data: SuggestionCreate,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = SuggestionService(db)
    return svc.submit_suggestion(
        agent_id,
        title=data.title,
        content=data.content,
        category=data.category,
        priority=data.priority,
    )


@router.get("")
def list_suggestions(
    s: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    current_agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = SuggestionService(db)
    result = svc.list_suggestions(
        status=s, category=category, agent_id=agent_id,
        limit=limit, offset=offset,
    )
    return result


@router.get("/leaderboard")
def get_leaderboard(
    limit: int = Query(20, ge=1),
    db: Session = Depends(get_db),
):
    svc = SuggestionService(db)
    return svc.get_leaderboard(limit=limit)


@router.get("/{suggestion_id}", response_model=SuggestionResponse)
def get_suggestion(
    suggestion_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = SuggestionService(db)
    return svc.get_suggestion(suggestion_id)


@router.put("/{suggestion_id}/status", response_model=SuggestionResponse)
def update_suggestion_status(
    suggestion_id: str,
    data: SuggestionStatusUpdate,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = SuggestionService(db)
    return svc.resolve_suggestion(
        suggestion_id,
        resolver_agent_id=agent_id,
        rejection_reason=data.rejection_reason,
    )


@router.post("/{suggestion_id}/replies", status_code=status.HTTP_201_CREATED, response_model=SuggestionReplyResponse)
def add_reply(
    suggestion_id: str,
    data: SuggestionReplyCreate,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = SuggestionService(db)
    return svc.add_reply(suggestion_id, agent_id, data.content)
