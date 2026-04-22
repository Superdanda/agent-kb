from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.modules.task_board.models.task_material import MaterialType


class TaskMaterialCreate(BaseModel):
    task_id: str
    material_type: MaterialType
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    order_index: int = 0
    is_result: bool = False


class TaskMaterialUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    order_index: Optional[int] = None
    is_result: Optional[bool] = None


class TaskMaterialResponse(BaseModel):
    id: str
    task_id: str
    material_type: MaterialType
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    order_index: int
    is_result: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
