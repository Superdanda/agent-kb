from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    title: str = Field(..., max_length=512)
    summary: Optional[str] = None
    content_md: Optional[str] = None
    tags: List[str] = []
    visibility: str = "PUBLIC_INTERNAL"
    status: str = "DRAFT"
    domain_id: str


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=512)
    summary: Optional[str] = None
    content_md: Optional[str] = None
    change_type: str = "MINOR"
    change_note: Optional[str] = None
    visibility: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    domain_id: Optional[str] = None


class PostVersionResponse(BaseModel):
    id: str
    post_id: str
    version_no: int
    title_snapshot: str
    summary_snapshot: Optional[str]
    content_md: Optional[str]
    change_type: str
    change_note: Optional[str]
    created_by_agent_id: str
    created_at: datetime
    author_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PostResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str]
    author_agent_id: str
    current_version_no: int
    latest_version_id: str
    visibility: str
    status: str
    tags_json: list
    created_at: datetime
    updated_at: datetime
    author_name: Optional[str] = None
    latest_version: Optional[PostVersionResponse] = None
    version_count: int = 0
    asset_count: int = 0
    learning_status: Optional[str] = None
    domain_id: Optional[str] = None
    domain_code: Optional[str] = None
    domain_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PostListItem(BaseModel):
    id: str
    title: str
    summary: Optional[str]
    author_name: Optional[str]
    current_version_no: int
    status: str
    tags_json: list
    updated_at: datetime
    learning_count: int = 0
    domain_id: Optional[str] = None
    domain_code: Optional[str] = None
    domain_name: Optional[str] = None

    model_config = {"from_attributes": True}
