from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.api.schemas.agent_registration import (
    AgentRegistrationCreate,
    AgentRegistrationResponse,
    AgentCredentialsResponse,
)
from app.services.agent_registration_service import AgentRegistrationService

router = APIRouter(prefix="/agent-registrations", tags=["agent-registrations"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_agent(data: AgentRegistrationCreate, db: Session = Depends(get_db)):
    """Submit a new agent registration request. Returns registration code for tracking."""
    svc = AgentRegistrationService(db)
    request, registration_code = svc.create_registration_request(data)
    return {
        "registration_code": registration_code,
        "message": "Registration request submitted. Use the registration code to check status.",
    }


@router.get("/{code}/status", response_model=AgentRegistrationResponse)
def check_status(code: str, db: Session = Depends(get_db)):
    """Check the status of a registration request by its code."""
    svc = AgentRegistrationService(db)
    request = svc.get_by_code(code)
    if not request:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Registration request with code {code} not found")
    return AgentRegistrationResponse.from_request(request)


@router.get("/agent/{agent_code}/records")
def get_agent_registration_records(
    agent_code: str,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """Get all registration records for a given agent_code with pagination."""
    svc = AgentRegistrationService(db)
    records, total = svc.get_by_agent_code(agent_code, page, page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return {
        "agent_code": agent_code,
        "records": [AgentRegistrationResponse.from_request(r) for r in records],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{code}/credentials")
def get_credentials(
    code: str,
    db: Session = Depends(get_db),
):
    """Get credentials for an approved registration. Uses registration code as authentication."""
    svc = AgentRegistrationService(db)
    request = svc.get_by_code(code)
    if not request:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Registration request with code {code} not found")
    
    if request.status.value != "APPROVED":
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("Registration is not yet approved")
    
    from app.services.agent_service import AgentService
    agent_svc = AgentService(db)
    agent = agent_svc.get_by_code(request.agent_code)
    
    if not agent or agent.agent_code != request.agent_code:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("Agent ID does not match registration")
    
    creds = agent.credentials.filter_by(status="ACTIVE").first()
    if not creds:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError("No active credentials found")
    
    from app.core.security import decrypt_secret
    secret_key = decrypt_secret(creds.secret_key_encrypted)
    
    return AgentCredentialsResponse(
        registration_code=code,
        agent_id=agent.id,
        agent_code=agent.agent_code,
        name=agent.name,
        access_key=creds.access_key,
        secret_key=secret_key,
    )
