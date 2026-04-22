from datetime import datetime

from pydantic import BaseModel, Field


class AdminUserCreate(BaseModel):
    username: str = Field(..., max_length=64)
    password: str = Field(..., min_length=6)


class AdminUserLogin(BaseModel):
    username: str
    password: str


class AdminUserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
