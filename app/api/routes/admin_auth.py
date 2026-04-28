from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.api.middleware.admin_auth import (
    verify_password,
    create_access_token,
    get_current_admin,
)


router = APIRouter(prefix="/api/admin", tags=["admin"])


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminResponse(BaseModel):
    id: int
    username: str
    nickname: str | None = None
    avatar_url: str | None = None
    created_at: str

    class Config:
        from_attributes = True


@router.post("/login")
async def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    admin = db.query(AdminUser).filter(AdminUser.username == request.username).first()
    if not admin or not verify_password(request.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if admin.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin user is inactive",
        )

    access_token = create_access_token(
        data={"admin_id": admin.id, "username": admin.username}
    )
    response.set_cookie(
        key="admin_token",
        value=access_token,
        httponly=True,
        max_age=24 * 60 * 60,
        samesite="lax",
    )
    return {"message": "Login successful", "username": admin.username}


@router.post("/logout", include_in_schema=False)
async def logout_post(response: Response):
    response.delete_cookie(key="admin_token")
    return {"message": "Logout successful"}


@router.get("/logout", include_in_schema=False)
async def logout_get(response: Response):
    response.delete_cookie(key="admin_token")
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/login", status_code=302)


@router.get("/me", response_model=AdminResponse)
async def get_me(current_admin: AdminUser = Depends(get_current_admin)):
    return AdminResponse(
        id=current_admin.id,
        username=current_admin.username,
        nickname=current_admin.nickname,
        avatar_url=current_admin.avatar_url,
        created_at=current_admin.created_at.isoformat(),
    )
