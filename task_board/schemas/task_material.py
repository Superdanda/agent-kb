from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.task_board.models.task_material import MaterialType


class TaskMaterialCreate(BaseModel):
    task_id: str
    material_type: MaterialType
    title: str = Field(..., max_length=256)
    content: Optional[str] = None
    url: Optional[str] = Field(None, max_length=1024)
    file_path: Optional[str] = Field(None, max_length=512)
    order_index: int = 0


class TaskMaterialUpdate(BaseModel):
    material_type: Optional[MaterialType] = None
    title: Optional[str] = Field(None, max_length=256)
    content: Optional[str] = None
    url: Optional[str] = Field(None, max_length=1024)
    file_path: Optional[str] = Field(None, max_length=512)
    order_index: Optional[int] = None


class TaskMaterialResponse(BaseModel):
    id: str
    task_id: str
    material_type: MaterialType
    title: str
    content: Optional[str]
    url: Optional[str]
    file_path: Optional[str]
    order_index: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
