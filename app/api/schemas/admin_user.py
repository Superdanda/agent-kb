from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AdminUserCreate(BaseModel):
    username: str = Field(..., max_length=64)
    password: str = Field(..., min_length=6)
    nickname: Optional[str] = Field(None, max_length=128)
    bio: Optional[str] = None
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=64)
    status: str = Field("ACTIVE", max_length=32)


class AdminUserUpdate(BaseModel):
    nickname: Optional[str] = Field(None, max_length=128)
    bio: Optional[str] = None
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = Field(None, max_length=32)
    password: Optional[str] = Field(None, min_length=6)


class AdminUserLogin(BaseModel):
    username: str
    password: str


class AdminUserResponse(BaseModel):
    id: int
    uuid: Optional[str] = None
    username: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
