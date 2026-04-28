from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.api.middleware.admin_auth import get_current_admin
from app.models.admin_user import AdminUser
from app.models.agent import Agent, AgentStatus
from app.models.credential import AgentCredential
from app.repositories.agent_repo import AgentRepository
from app.core.security import encrypt_secret, decrypt_secret
import secrets
import uuid

router = APIRouter(prefix="/admin/agents", tags=["admin-agents"])


def _mask_secret(value: str | None, keep_start: int = 6, keep_end: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep_start + keep_end:
        return value[:1] + "***" + value[-1:]
    return f"{value[:keep_start]}***{value[-keep_end:]}"


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    agent_type: Optional[str] = None
    device_name: Optional[str] = None
    callback_url: Optional[str] = None
    environment_tags: Optional[list[str]] = None
    capabilities: Optional[str] = None
    self_introduction: Optional[str] = None
    work_preferences: Optional[dict] = None
    status: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    agent_code: str
    name: str
    agent_type: Optional[str]
    device_name: Optional[str]
    callback_url: Optional[str]
    environment_tags: Optional[list[str]]
    capabilities: Optional[str]
    self_introduction: Optional[str]
    work_preferences: Optional[dict]
    status: str
    created_at: str

    model_config = {"from_attributes": True}


class AgentCredentialItem(BaseModel):
    access_key: str
    secret_key: str

    model_config = {"from_attributes": True}


class AgentCredentialsResponse(BaseModel):
    agent_id: str
    credentials: list[AgentCredentialItem]


@router.get("", response_model=list[AgentResponse])
def list_agents(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """List all agents."""
    repo = AgentRepository(db)
    agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    return [
        AgentResponse(
            id=a.id,
            agent_code=a.agent_code,
            name=a.name,
            agent_type=a.agent_type,
            device_name=a.device_name,
            callback_url=a.callback_url,
            environment_tags=a.environment_tags,
            capabilities=a.capabilities,
            self_introduction=a.self_introduction,
            work_preferences=a.work_preferences,
            status=a.status.value,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Get a specific agent by ID."""
    repo = AgentRepository(db)
    agent = repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return AgentResponse(
        id=agent.id,
        agent_code=agent.agent_code,
        name=agent.name,
        agent_type=agent.agent_type,
        device_name=agent.device_name,
        callback_url=agent.callback_url,
        environment_tags=agent.environment_tags,
        capabilities=agent.capabilities,
        self_introduction=agent.self_introduction,
        work_preferences=agent.work_preferences,
        status=agent.status.value,
        created_at=agent.created_at.isoformat() if agent.created_at else "",
    )


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    data: AgentUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Update agent information."""
    repo = AgentRepository(db)
    agent = repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    if data.name is not None:
        agent.name = data.name
    if data.agent_type is not None:
        agent.agent_type = data.agent_type.strip() or None
    if data.device_name is not None:
        agent.device_name = data.device_name
    if data.callback_url is not None:
        agent.callback_url = data.callback_url.strip() or None
    if data.environment_tags is not None:
        agent.environment_tags = data.environment_tags
    if data.capabilities is not None:
        agent.capabilities = data.capabilities
    if data.self_introduction is not None:
        agent.self_introduction = data.self_introduction
    if data.work_preferences is not None:
        agent.work_preferences = data.work_preferences
    if data.status is not None:
        try:
            agent.status = AgentStatus(data.status.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {data.status}")

    db.commit()
    db.refresh(agent)
    return AgentResponse(
        id=agent.id,
        agent_code=agent.agent_code,
        name=agent.name,
        agent_type=agent.agent_type,
        device_name=agent.device_name,
        callback_url=agent.callback_url,
        environment_tags=agent.environment_tags,
        capabilities=agent.capabilities,
        self_introduction=agent.self_introduction,
        work_preferences=agent.work_preferences,
        status=agent.status.value,
        created_at=agent.created_at.isoformat() if agent.created_at else "",
    )


@router.post("/{agent_id}/deactivate", status_code=status.HTTP_200_OK)
def deactivate_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Deactivate an agent."""
    repo = AgentRepository(db)
    agent = repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    agent.status = AgentStatus.INACTIVE
    db.commit()
    return {"message": "Agent deactivated", "agent_id": agent_id, "status": "INACTIVE"}


@router.post("/{agent_id}/reactivate", status_code=status.HTTP_200_OK)
def reactivate_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Reactivate an agent."""
    repo = AgentRepository(db)
    agent = repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    agent.status = AgentStatus.ACTIVE
    db.commit()
    return {"message": "Agent reactivated", "agent_id": agent_id, "status": "ACTIVE"}


@router.get("/{agent_id}/credentials", response_model=AgentCredentialsResponse)
def get_agent_credentials(
    agent_id: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Get active credentials for an agent with masked secrets."""
    repo = AgentRepository(db)
    agent = repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    active_creds = (
        db.query(AgentCredential)
        .filter(
            AgentCredential.agent_id == agent_id,
            AgentCredential.status == "ACTIVE",
        )
        .all()
    )
    if not active_creds:
        raise HTTPException(
            status_code=404,
            detail=f"No active credentials found for agent {agent_id}. Call POST /reset-credentials first.",
        )

    return AgentCredentialsResponse(
        agent_id=agent_id,
        credentials=[
            AgentCredentialItem(
                access_key=_mask_secret(c.access_key),
                secret_key=_mask_secret(decrypt_secret(c.secret_key_encrypted)),
            )
            for c in active_creds
        ],
    )


@router.post("/{agent_id}/credentials", response_model=AgentCredentialsResponse)
def create_agent_credentials(
    agent_id: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Create a new credential pair for an agent (does not invalidate existing ones)."""
    repo = AgentRepository(db)
    agent = repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    access_key = secrets.token_urlsafe(24)[:32]
    secret_key = secrets.token_urlsafe(48)[:64]
    encrypted = encrypt_secret(secret_key)

    new_cred = AgentCredential(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        access_key=access_key,
        secret_key_encrypted=encrypted,
        status="ACTIVE",
    )
    db.add(new_cred)
    db.commit()
    db.refresh(new_cred)

    return AgentCredentialsResponse(
        agent_id=agent_id,
        credentials=[
            AgentCredentialItem(
                access_key=_mask_secret(new_cred.access_key),
                secret_key=_mask_secret(secret_key),
            )
        ],
    )


@router.post("/{agent_id}/reset-credentials", status_code=status.HTTP_200_OK)
def reset_credentials(
    agent_id: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Reset agent credentials (invalidate all existing, return new access/secret keys)."""
    repo = AgentRepository(db)
    agent = repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Deactivate all existing credentials
    existing_creds = db.query(AgentCredential).filter(
        AgentCredential.agent_id == agent_id,
        AgentCredential.status == "ACTIVE",
    ).all()
    for cred in existing_creds:
        cred.status = "INACTIVE"

    # Create new credentials
    access_key = secrets.token_urlsafe(24)[:32]
    secret_key = secrets.token_urlsafe(48)[:64]
    encrypted = encrypt_secret(secret_key)

    new_cred = AgentCredential(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        access_key=access_key,
        secret_key_encrypted=encrypted,
        status="ACTIVE",
    )
    db.add(new_cred)
    db.commit()

    return {
        "message": "Credentials reset successfully",
        "agent_id": agent_id,
        "access_key": access_key,
        "secret_key": secret_key,
        "access_key_masked": _mask_secret(access_key),
        "secret_key_masked": _mask_secret(secret_key),
    }


@router.post("/{agent_id}/revoke-credentials", status_code=status.HTTP_200_OK)
def revoke_credentials(
    agent_id: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Deactivate all active credentials for an agent without creating a replacement."""
    repo = AgentRepository(db)
    agent = repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    active_creds = db.query(AgentCredential).filter(
        AgentCredential.agent_id == agent_id,
        AgentCredential.status == "ACTIVE",
    ).all()
    for cred in active_creds:
        cred.status = "INACTIVE"
    db.commit()

    return {
        "message": "Credentials revoked successfully",
        "agent_id": agent_id,
        "revoked_count": len(active_creds),
    }


@router.delete("/{agent_id}", status_code=status.HTTP_200_OK)
def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Delete an agent and all its credentials."""
    repo = AgentRepository(db)
    agent = repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Delete credentials first
    db.query(AgentCredential).filter(AgentCredential.agent_id == agent_id).delete()

    # Delete the agent
    db.delete(agent)
    db.commit()

    return {"message": "Agent deleted", "agent_id": agent_id}
