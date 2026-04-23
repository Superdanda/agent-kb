from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.api.schemas.agent import AgentResponse
from app.services.agent_service import AgentService
from app.models.agent import AgentStatus

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/heartbeat")
def heartbeat(
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Update agent status to active (authenticated)."""
    svc = AgentService(db)
    agent = svc.update_status(agent_id, AgentStatus.ACTIVE)
    return {"status": "ok", "agent_id": agent.id}


@router.get("/me", response_model=AgentResponse)
def get_me(
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Get current agent info (authenticated)."""
    svc = AgentService(db)
    agent = svc.get_by_id(agent_id)
    if not agent:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Agent {agent_id} not found")
    return agent
