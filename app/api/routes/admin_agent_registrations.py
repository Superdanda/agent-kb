from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.api.middleware.admin_auth import get_current_admin
from app.api.schemas.agent_registration import AgentRegistrationResponse, AgentCredentialsResponse
from app.services.agent_registration_service import AgentRegistrationService
from app.models.admin_user import AdminUser
from app.utils.pagination import build_paginated_response

router = APIRouter(prefix="/admin/agent-registrations", tags=["admin-agent-registrations"])


class RejectRequest(BaseModel):
    reason: str


class PaginatedRegistrationsResponse(BaseModel):
    records: list[AgentRegistrationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=PaginatedRegistrationsResponse)
def list_registrations(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """List all agent registration requests with pagination."""
    svc = AgentRegistrationService(db)

    status_enum = None
    if status_filter:
        from app.models.agent_registration import RegistrationStatus
        try:
            status_enum = RegistrationStatus(status_filter.upper())
        except ValueError:
            from app.core.exceptions import ValidationError
            raise ValidationError(f"Invalid status: {status_filter}. Must be PENDING, APPROVED, or REJECTED")

    records, total = svc.list_all(status_enum, page, page_size)
    response = build_paginated_response(
        [AgentRegistrationResponse.from_request(r) for r in records],
        total, page, page_size
    )
    return PaginatedRegistrationsResponse(**response)


@router.get("/{request_id}", response_model=AgentRegistrationResponse)
def get_registration(
    request_id: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Get details of a specific registration request."""
    svc = AgentRegistrationService(db)
    request = svc.get_by_id(request_id)
    if not request:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Registration request {request_id} not found")
    return AgentRegistrationResponse.from_request(request)


@router.post("/{request_id}/approve", status_code=status.HTTP_200_OK)
def approve_registration(
    request_id: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Approve a registration request and create the agent with credentials."""
    svc = AgentRegistrationService(db)
    agent, cred, secret_key = svc.approve_registration(request_id, current_admin.username)
    return {
        "message": "Registration approved and agent created",
        "agent": {
            "id": agent.id,
            "agent_code": agent.agent_code,
            "name": agent.name,
            "status": agent.status.value,
        },
        "credentials": {
            "access_key": cred.access_key,
            "secret_key": secret_key,
        },
    }


@router.post("/{request_id}/reject", status_code=status.HTTP_200_OK)
def reject_registration(
    request_id: str,
    body: RejectRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    """Reject a registration request with a reason."""
    svc = AgentRegistrationService(db)
    request = svc.reject_registration(request_id, body.reason)
    return {
        "message": "Registration rejected",
        "registration_code": request.registration_code,
        "reason": body.reason,
    }
