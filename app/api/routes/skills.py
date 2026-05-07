from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.middleware.admin_auth import get_current_admin
from app.api.middleware.auth import get_current_agent
from app.api.schemas.skill import (
    SkillAdminUpdate,
    SkillResponse,
    SkillUpdateCheckRequest,
    SkillUpdateCheckResponse,
    SkillUploadResponse,
    SkillVersionResponse,
)
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.services.skill_service import SkillService
from app.utils.pagination import calculate_total_pages

router = APIRouter(prefix="/skills", tags=["skills"])
admin_router = APIRouter(prefix="/admin/skills", tags=["admin_skills"])


@router.post("/upload", response_model=SkillUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_skill(
    file: UploadFile = File(...),
    release_note: Optional[str] = Form(None),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = SkillService(db)
    skill, version = svc.upload_skill_package(
        file=file,
        uploader_agent_id=agent_id,
        release_note=release_note,
    )
    return {
        "skill_id": skill.id,
        "version_id": version.id,
        "slug": skill.slug,
        "version": version.version,
    }


@router.get("")
def list_skills(
    keyword: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    uploader_agent_id: Optional[str] = Query(None),
    recommended_only: bool = Query(False),
    official_only: bool = Query(False),
    important_only: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = SkillService(db)
    skills, total = svc.list_skills(
        keyword=keyword,
        tags=tags,
        uploader_agent_id=uploader_agent_id,
        recommended_only=recommended_only,
        official_only=official_only,
        important_only=important_only,
        page=page,
        size=size,
    )
    return {"items": skills, "total": total, "page": page, "size": size, "total_pages": calculate_total_pages(total, size)}


@router.get("/{skill_id}", response_model=SkillResponse)
def get_skill(
    skill_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    return SkillService(db).get_skill(skill_id)


@router.get("/{skill_id}/versions", response_model=list[SkillVersionResponse])
def get_skill_versions(
    skill_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    return SkillService(db).get_skill_versions(skill_id)


@router.get("/{skill_id}/download")
def download_skill(
    skill_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    data, filename, mime_type = SkillService(db).download_skill_latest(skill_id)
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.get("/versions/{version_id}/download")
def download_skill_version(
    version_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    data, filename, mime_type = SkillService(db).download_skill_version(version_id)
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.post("/check-update", response_model=SkillUpdateCheckResponse)
def check_skill_update(
    data: SkillUpdateCheckRequest,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    return SkillService(db).check_update(data.slug, data.current_version)


@admin_router.put("/{skill_id}", response_model=SkillResponse)
def update_skill_admin(
    skill_id: str,
    data: SkillAdminUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return SkillService(db).update_skill_admin(skill_id, **data.model_dump(exclude_none=True))


@admin_router.put("/versions/{version_id}", response_model=SkillVersionResponse)
def update_skill_version_status(
    version_id: str,
    status_value: str = Query(..., alias="status"),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return SkillService(db).update_version_status(version_id, status_value)
