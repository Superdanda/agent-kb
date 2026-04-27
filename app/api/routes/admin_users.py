from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.middleware.admin_auth import get_current_admin
from app.api.schemas.admin_user import AdminUserCreate, AdminUserResponse, AdminUserUpdate
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.services.admin_user_service import AdminUserService


router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("")
def list_admin_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    admins, total = AdminUserService(db).list_admins(page=page, size=size, keyword=keyword)
    return {
        "items": [AdminUserResponse.model_validate(admin) for admin in admins],
        "total": total,
        "page": page,
        "size": size,
    }


@router.post("", response_model=AdminUserResponse, status_code=201)
def create_admin_user(
    data: AdminUserCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    return AdminUserService(db).create_admin(data)


@router.get("/{admin_id}", response_model=AdminUserResponse)
def get_admin_user(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    return AdminUserService(db).get_admin(admin_id)


@router.put("/{admin_id}", response_model=AdminUserResponse)
def update_admin_user(
    admin_id: int,
    data: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    return AdminUserService(db).update_admin(admin_id, data)


@router.post("/{admin_id}/avatar", response_model=AdminUserResponse)
def upload_admin_avatar(
    admin_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    return AdminUserService(db).upload_avatar(admin_id, file)
