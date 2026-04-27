import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.api.middleware.admin_auth import get_password_hash
from app.api.schemas.admin_user import AdminUserCreate, AdminUserUpdate
from app.core.exceptions import AlreadyExistsError, FileValidationError, ResourceNotFoundError, ValidationError
from app.core.file_storage import get_default_bucket, read_upload_buffer, upload_bytes_to_storage
from app.models.admin_user import AdminUser
from app.repositories.admin_user_repo import AdminUserRepository
from app.utils.file_check import validate_magic_number


ACTIVE_STATUS = "ACTIVE"
INACTIVE_STATUS = "INACTIVE"
ADMIN_STATUSES = {ACTIVE_STATUS, INACTIVE_STATUS}
AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png"}
AVATAR_MAGIC_TYPES = {"jpg", "png"}


class AdminUserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdminUserRepository(db)

    def list_admins(self, *, page: int = 1, size: int = 20, keyword: str | None = None) -> tuple[list[AdminUser], int]:
        return self.repo.list(page=page, size=size, keyword=keyword)

    def get_admin(self, admin_id: int) -> AdminUser:
        admin = self.repo.get_by_id(admin_id)
        if not admin:
            raise ResourceNotFoundError(f"Admin user {admin_id} not found")
        return admin

    def create_admin(self, data: AdminUserCreate) -> AdminUser:
        username = data.username.strip()
        if not username:
            raise ValidationError("Username is required")
        if self.repo.get_by_username(username):
            raise AlreadyExistsError(f"Admin user {username} already exists")

        status = self._normalize_status(data.status)
        admin = AdminUser(
            uuid=str(uuid.uuid4()),
            username=username,
            password_hash=get_password_hash(data.password),
            nickname=self._clean_optional(data.nickname),
            bio=self._clean_optional(data.bio),
            email=self._clean_optional(data.email),
            phone=self._clean_optional(data.phone),
            status=status,
        )
        return self.repo.create(admin)

    def update_admin(self, admin_id: int, data: AdminUserUpdate) -> AdminUser:
        admin = self.get_admin(admin_id)
        update_data = data.model_dump(exclude_unset=True)

        if "nickname" in update_data:
            admin.nickname = self._clean_optional(data.nickname)
        if "bio" in update_data:
            admin.bio = self._clean_optional(data.bio)
        if "email" in update_data:
            admin.email = self._clean_optional(data.email)
        if "phone" in update_data:
            admin.phone = self._clean_optional(data.phone)
        if "status" in update_data and data.status is not None:
            admin.status = self._normalize_status(data.status)
        if "password" in update_data and data.password:
            admin.password_hash = get_password_hash(data.password)

        admin.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(admin)
        return admin

    def upload_avatar(self, admin_id: int, file: UploadFile) -> AdminUser:
        admin = self.get_admin(admin_id)
        if not admin.uuid:
            admin.uuid = str(uuid.uuid4())

        upload = read_upload_buffer(file)
        file_ext = upload.file_ext.lower()
        if file_ext not in AVATAR_EXTENSIONS:
            raise FileValidationError("Avatar must be a JPG or PNG image")

        is_valid_magic, magic_type = validate_magic_number(upload.contents[:64])
        if not is_valid_magic or magic_type not in AVATAR_MAGIC_TYPES:
            raise FileValidationError("Avatar content must be a valid JPG or PNG image")

        object_key = f"admin_avatars/{admin.uuid}/{uuid.uuid4()}{file_ext}"
        avatar_url = upload_bytes_to_storage(
            bucket=get_default_bucket(),
            object_key=object_key,
            data=upload.contents,
            content_type=upload.content_type,
            failure_message="Failed to upload avatar",
        )
        admin.avatar_object_key = object_key
        admin.avatar_url = avatar_url
        admin.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(admin)
        return admin

    def _normalize_status(self, status: str) -> str:
        value = (status or ACTIVE_STATUS).upper()
        if value not in ADMIN_STATUSES:
            raise ValidationError(f"Invalid admin status: {status}")
        return value

    def _clean_optional(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
