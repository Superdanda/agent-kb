from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.api.schemas.domain import DomainCreate, DomainUpdate, DomainResponse
from app.services.domain_service import DomainService

router = APIRouter(tags=["domains"])

@router.get("/domains", response_model=dict)
def list_domains(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
):
    """List all knowledge domains (public API, no auth required)"""
    svc = DomainService(db)
    domains = svc.get_all_domains(include_inactive=include_inactive)
    items = []
    for d in domains:
        items.append({
            "id": d.id,
            "code": d.code,
            "name": d.name,
            "description": d.description,
            "icon": d.icon,
            "color": d.color,
            "sort_order": d.sort_order,
            "is_active": d.is_active,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
            "post_count": d.posts.count() if d.posts else 0,
        })
    return {"items": items, "total": len(items)}

@router.get("/domains/{domain_id}", response_model=DomainResponse)
def get_domain(domain_id: str, db: Session = Depends(get_db)):
    """Get a single domain by ID (public API)"""
    svc = DomainService(db)
    d = svc.get_by_id(domain_id)
    return {
        "id": d.id,
        "code": d.code,
        "name": d.name,
        "description": d.description,
        "icon": d.icon,
        "color": d.color,
        "sort_order": d.sort_order,
        "is_active": d.is_active,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
        "post_count": d.posts.count() if d.posts else 0,
    }

@router.post("/domains", response_model=dict, status_code=201)
def create_domain(
    data: DomainCreate,
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_current_agent),
):
    """Create a new knowledge domain (requires auth)"""
    svc = DomainService(db)
    domain = svc.create_domain(
        code=data.code,
        name=data.name,
        description=data.description,
        icon=data.icon,
        color=data.color,
        sort_order=data.sort_order,
    )
    return {"id": domain.id, "code": domain.code, "name": domain.name}

@router.patch("/domains/{domain_id}", response_model=dict)
def update_domain(
    domain_id: str,
    data: DomainUpdate,
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_current_agent),
):
    """Update a knowledge domain (requires auth)"""
    svc = DomainService(db)
    domain = svc.update_domain(
        domain_id=domain_id,
        name=data.name,
        description=data.description,
        icon=data.icon,
        color=data.color,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    return {"id": domain.id, "code": domain.code, "name": domain.name}

@router.delete("/domains/{domain_id}", response_model=dict)
def delete_domain(
    domain_id: str,
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_current_agent),
):
    """Delete a knowledge domain (requires auth, fails if posts exist)"""
    svc = DomainService(db)
    svc.delete_domain(domain_id)
    return {"message": "Domain deleted"}
