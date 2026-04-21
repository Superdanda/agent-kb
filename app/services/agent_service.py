import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import encrypt_secret
from app.core.exceptions import AlreadyExistsError
from app.models.credential import AgentCredential
from app.models.agent import Agent, AgentStatus
from app.repositories.agent_repo import AgentRepository


class AgentService:
    def __init__(self, db: Session):
        self.repo = AgentRepository(db)
        self.db = db

    def create_agent(self, data) -> Agent:
        existing = self.repo.get_by_code(data.agent_code)
        if existing:
            raise AlreadyExistsError(f"Agent {data.agent_code} already exists")

        agent = Agent(
            id=str(uuid.uuid4()),
            agent_code=data.agent_code,
            name=data.name,
            device_name=data.device_name,
            environment_tags=data.environment_tags or [],
            status=AgentStatus.ACTIVE,
        )
        return self.repo.create(agent)

    def get_by_code(self, code: str) -> Agent | None:
        return self.repo.get_by_code(code)

    def get_by_id(self, id: str) -> Agent | None:
        return self.repo.get_by_id(id)

    def get_by_access_key(self, access_key: str) -> Agent | None:
        return self.repo.get_by_access_key(access_key)

    def create_credential(self, agent_id: str) -> tuple[AgentCredential, str]:
        access_key = secrets.token_urlsafe(24)[:32]
        secret_key = secrets.token_urlsafe(48)[:64]
        encrypted = encrypt_secret(secret_key)

        cred = AgentCredential(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            access_key=access_key,
            secret_key_encrypted=encrypted,
            status="ACTIVE",
        )
        return self.repo.create_credential(cred), secret_key

    def update_status(self, agent_id: str, status: AgentStatus) -> Agent:
        agent = self.repo.get_by_id(agent_id)
        if not agent:
            from app.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError(f"Agent {agent_id} not found")
        agent.status = status
        self.db.commit()
        self.db.refresh(agent)
        return agent
