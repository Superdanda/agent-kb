from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.models.credential import AgentCredential


class AgentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, agent: Agent) -> Agent:
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def get_by_id(self, id: str) -> Agent | None:
        return self.db.query(Agent).filter(Agent.id == id).first()

    def get_by_code(self, code: str) -> Agent | None:
        return self.db.query(Agent).filter(Agent.agent_code == code).first()

    def get_by_access_key(self, access_key: str) -> Agent | None:
        cred = self.db.query(AgentCredential).filter(
            AgentCredential.access_key == access_key
        ).first()
        if not cred:
            return None
        return self.db.query(Agent).filter(Agent.id == cred.agent_id).first()

    def create_credential(self, cred: AgentCredential) -> AgentCredential:
        self.db.add(cred)
        self.db.commit()
        self.db.refresh(cred)
        return cred
