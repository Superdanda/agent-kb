from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class DomainCreate(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=64)
    color: Optional[str] = Field(None, max_length=16)
    sort_order: int = 0


class DomainUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=64)
    color: Optional[str] = Field(None, max_length=16)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class DomainResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    post_count: int = 0

    model_config = {"from_attributes": True}


class DomainListResponse(BaseModel):
    items: List[DomainResponse]
    total: int
