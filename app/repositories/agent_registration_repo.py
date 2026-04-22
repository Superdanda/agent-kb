from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.agent_registration import AgentRegistrationRequest, RegistrationStatus


class AgentRegistrationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, request: AgentRegistrationRequest) -> AgentRegistrationRequest:
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def get_by_id(self, id: str) -> Optional[AgentRegistrationRequest]:
        return self.db.query(AgentRegistrationRequest).filter(AgentRegistrationRequest.id == id).first()

    def get_by_code(self, code: str) -> Optional[AgentRegistrationRequest]:
        return self.db.query(AgentRegistrationRequest).filter(AgentRegistrationRequest.registration_code == code).first()

    def list_pending(self) -> list[AgentRegistrationRequest]:
        return self.db.query(AgentRegistrationRequest).filter(
            AgentRegistrationRequest.status == RegistrationStatus.PENDING
        ).order_by(AgentRegistrationRequest.created_at.desc()).all()

    def list_all(
        self,
        status: Optional[RegistrationStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AgentRegistrationRequest], int]:
        query = self.db.query(AgentRegistrationRequest)
        if status:
            query = query.filter(AgentRegistrationRequest.status == status)
        total = query.count()
        records = (
            query.order_by(AgentRegistrationRequest.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return records, total

    def get_by_agent_code(
        self, agent_code: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[AgentRegistrationRequest], int]:
        query = self.db.query(AgentRegistrationRequest).filter(
            AgentRegistrationRequest.agent_code == agent_code
        )
        total = query.count()
        records = (
            query.order_by(AgentRegistrationRequest.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return records, total

    def update_status(
        self,
        request: AgentRegistrationRequest,
        status: RegistrationStatus,
        rejection_reason: Optional[str] = None,
        admin_notes: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> AgentRegistrationRequest:
        request.status = status
        if status == RegistrationStatus.APPROVED:
            request.approved_at = datetime.now(timezone.utc)
            request.approved_by = approved_by
        if rejection_reason:
            request.rejection_reason = rejection_reason
        if admin_notes:
            request.admin_notes = admin_notes
        self.db.commit()
        self.db.refresh(request)
        return request
