import io

import pytest
from fastapi import Response, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.middleware.admin_auth import verify_password
from app.api.routes.admin_auth import LoginRequest, login
from app.api.schemas.admin_user import AdminUserCreate, AdminUserUpdate
from app.core.database import Base
from app.core.exceptions import FileValidationError
from app.models.admin_user import AdminUser
from app.services.admin_user_service import AdminUserService


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def make_upload(filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content), headers={"content-type": content_type})


def test_create_admin_hashes_password_and_defaults_active(db):
    admin = AdminUserService(db).create_admin(
        AdminUserCreate(
            username="manager",
            password="secret123",
            nickname="Manager",
            bio="Human admin",
        )
    )

    assert admin.username == "manager"
    assert admin.nickname == "Manager"
    assert admin.bio == "Human admin"
    assert admin.status == "ACTIVE"
    assert admin.uuid
    assert verify_password("secret123", admin.password_hash)


def test_update_admin_profile_and_optional_password(db):
    service = AdminUserService(db)
    admin = service.create_admin(AdminUserCreate(username="manager", password="secret123"))

    updated = service.update_admin(
        admin.id,
        AdminUserUpdate(
            nickname="Lead",
            email="lead@example.com",
            phone="123",
            bio="Updated intro",
            status="INACTIVE",
            password="newsecret",
        ),
    )

    assert updated.nickname == "Lead"
    assert updated.email == "lead@example.com"
    assert updated.phone == "123"
    assert updated.bio == "Updated intro"
    assert updated.status == "INACTIVE"
    assert verify_password("newsecret", updated.password_hash)


@pytest.mark.asyncio
async def test_inactive_admin_cannot_login(db):
    service = AdminUserService(db)
    service.create_admin(
        AdminUserCreate(username="manager", password="secret123", status="INACTIVE")
    )

    with pytest.raises(Exception) as exc_info:
        await login(LoginRequest(username="manager", password="secret123"), Response(), db)

    assert getattr(exc_info.value, "status_code", None) == 403


def test_upload_avatar_accepts_png_and_stores_url(db, monkeypatch):
    service = AdminUserService(db)
    admin = service.create_admin(AdminUserCreate(username="manager", password="secret123"))
    calls = []

    def fake_upload(**kwargs):
        calls.append(kwargs)
        return f"/mock/{kwargs['object_key']}"

    monkeypatch.setattr("app.services.admin_user_service.upload_bytes_to_storage", fake_upload)

    updated = service.upload_avatar(
        admin.id,
        make_upload("avatar.png", b"\x89PNG\r\n\x1a\npayload", "image/png"),
    )

    assert updated.avatar_url.startswith("/mock/admin_avatars/")
    assert updated.avatar_object_key == calls[0]["object_key"]
    assert calls[0]["content_type"] == "image/png"


def test_upload_avatar_rejects_non_image(db):
    service = AdminUserService(db)
    admin = service.create_admin(AdminUserCreate(username="manager", password="secret123"))

    with pytest.raises(FileValidationError):
        service.upload_avatar(
            admin.id,
            make_upload("avatar.txt", b"plain text", "text/plain"),
        )
