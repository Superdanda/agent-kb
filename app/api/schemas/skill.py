from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SkillUploadResponse(BaseModel):
    skill_id: str
    version_id: str
    slug: str
    version: str


class SkillVersionResponse(BaseModel):
    id: str
    skill_id: str
    version: str
    summary_snapshot: Optional[str] = None
    tags_snapshot: list[str] = []
    release_note: Optional[str] = None
    package_filename: str
    file_size: int
    sha256: str
    mime_type: Optional[str] = None
    metadata_json: dict[str, Any] = {}
    created_by_agent_id: Optional[str] = None
    created_by_admin_uuid: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    uploader_name: Optional[str] = None

    model_config = {"from_attributes": True}


class SkillResponse(BaseModel):
    id: str
    slug: str
    name: str
    summary: Optional[str] = None
    tags_json: list[str] = []
    current_version_id: Optional[str] = None
    uploader_agent_id: Optional[str] = None
    uploader_admin_uuid: Optional[str] = None
    is_recommended: bool
    is_important: bool
    is_official: bool
    status: str
    created_at: datetime
    updated_at: datetime
    uploader_name: Optional[str] = None
    current_version: Optional[SkillVersionResponse] = None
    versions: list[SkillVersionResponse] = Field(default_factory=list, validation_alias="version_items")

    model_config = {"from_attributes": True, "populate_by_name": True}


class SkillListItem(BaseModel):
    id: str
    slug: str
    name: str
    summary: Optional[str] = None
    tags_json: list[str] = []
    is_recommended: bool
    is_important: bool
    is_official: bool
    status: str
    updated_at: datetime
    uploader_name: Optional[str] = None
    current_version: Optional[SkillVersionResponse] = None

    model_config = {"from_attributes": True}


class SkillUpdateCheckRequest(BaseModel):
    slug: str = Field(..., max_length=128)
    current_version: str = Field(..., max_length=64)


class SkillUpdateCheckResponse(BaseModel):
    slug: str
    current_version: str
    latest_version: Optional[str] = None
    has_update: bool
    download_url: Optional[str] = None
    skill_id: Optional[str] = None


class SkillAdminUpdate(BaseModel):
    is_recommended: Optional[bool] = None
    is_important: Optional[bool] = None
    is_official: Optional[bool] = None
    status: Optional[str] = None
