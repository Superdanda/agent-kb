import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AlreadyExistsError, ResourceNotFoundError
from app.core.security import encrypt_secret
from app.models.agent import Agent, AgentStatus
from app.models.agent_registration import AgentRegistrationRequest, RegistrationStatus
from app.models.credential import AgentCredential
from app.repositories.agent_registration_repo import AgentRegistrationRepository


def _generate_registration_code() -> str:
    """Generate a unique registration code in format AGT-XXXXXX."""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    suffix = "".join(secrets.choice(chars) for _ in range(6))
    return f"AGT-{suffix}"


class AgentRegistrationService:
    def __init__(self, db: Session):
        self.repo = AgentRegistrationRepository(db)
        self.db = db

    def create_registration_request(self, data) -> tuple[AgentRegistrationRequest, str]:
        """Create a new registration request and return (request, registration_code)."""
        existing = self.repo.get_by_code(data.agent_code)
        if existing:
            raise AlreadyExistsError(f"Agent code {data.agent_code} already has a registration request")

        registration_code = _generate_registration_code()
        while self.repo.get_by_code(registration_code):
            registration_code = _generate_registration_code()

        request = AgentRegistrationRequest(
            id=str(uuid.uuid4()),
            registration_code=registration_code,
            agent_code=data.agent_code,
            name=data.name,
            device_name=data.device_name,
            environment_tags=data.environment_tags or [],
            capabilities=data.capabilities,
            self_introduction=data.self_introduction,
            status=RegistrationStatus.PENDING,
        )
        request = self.repo.create(request)
        return request, registration_code

    def approve_registration(
        self, request_id: str, admin_username: str
    ) -> tuple[Agent, AgentCredential, str]:
        """Approve a registration and create the agent with credentials. Returns (agent, credential, secret_key)."""
        request = self.repo.get_by_id(request_id)
        if not request:
            raise ResourceNotFoundError(f"Registration request {request_id} not found")
        if request.status != RegistrationStatus.PENDING:
            raise AlreadyExistsError(f"Registration request is already {request.status.value}")

        # Check if agent_code already exists
        from app.models.agent import Agent
        existing = self.db.query(Agent).filter(Agent.agent_code == request.agent_code).first()
        if existing:
            raise AlreadyExistsError(f"Agent with code {request.agent_code} already exists. Please reject this request and ask the user to register with a different code.")

        agent = Agent(
            id=str(uuid.uuid4()),
            agent_code=request.agent_code,
            name=request.name,
            device_name=request.device_name,
            environment_tags=request.environment_tags or [],
            status=AgentStatus.ACTIVE,
            registration_request_id=request.id,
            approved_by_admin=True,
        )
        self.db.add(agent)
        self.db.flush()

        access_key = secrets.token_urlsafe(24)[:32]
        secret_key = secrets.token_urlsafe(48)[:64]
        encrypted = encrypt_secret(secret_key)

        cred = AgentCredential(
            id=str(uuid.uuid4()),
            agent_id=agent.id,
            access_key=access_key,
            secret_key_encrypted=encrypted,
            status="ACTIVE",
        )
        self.db.add(cred)
        self.db.flush()

        self.repo.update_status(request, RegistrationStatus.APPROVED, approved_by=admin_username)

        self.db.commit()
        self.db.refresh(agent)
        self.db.refresh(cred)

        return agent, cred, secret_key

    def reject_registration(
        self, request_id: str, reason: str
    ) -> AgentRegistrationRequest:
        """Reject a registration request with a reason."""
        request = self.repo.get_by_id(request_id)
        if not request:
            raise ResourceNotFoundError(f"Registration request {request_id} not found")
        if request.status != RegistrationStatus.PENDING:
            raise AlreadyExistsError(f"Registration request is already {request.status.value}")

        return self.repo.update_status(
            request, RegistrationStatus.REJECTED, rejection_reason=reason
        )

    def get_by_code(self, code: str) -> Optional[AgentRegistrationRequest]:
        """Get a registration request by its registration code."""
        return self.repo.get_by_code(code)

    def get_by_id(self, id: str) -> Optional[AgentRegistrationRequest]:
        """Get a registration request by ID."""
        return self.repo.get_by_id(id)

    def list_pending(self) -> list[AgentRegistrationRequest]:
        """List all pending registration requests."""
        return self.repo.list_pending()

    def get_by_agent_code(
        self, agent_code: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[AgentRegistrationRequest], int]:
        return self.repo.get_by_agent_code(agent_code, page, page_size)

    def list_all(
        self, status: Optional[RegistrationStatus] = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[AgentRegistrationRequest], int]:
        """List all registration requests with pagination."""
        return self.repo.list_all(status, page, page_size)
