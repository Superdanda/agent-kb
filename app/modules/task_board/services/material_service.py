import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from app.modules.task_board.models.task_material import TaskMaterial, MaterialType
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError


class MaterialService:
    def __init__(self, db: Session):
        self.db = db

    def create_material(
        self,
        task_id: str,
        material_type: MaterialType,
        title: str,
        content: Optional[str] = None,
        url: Optional[str] = None,
        file_path: Optional[str] = None,
        order_index: int = 0,
    ) -> TaskMaterial:
        material = TaskMaterial(
            id=str(uuid.uuid4()),
            task_id=task_id,
            material_type=material_type,
            title=title,
            content=content,
            url=url,
            file_path=file_path,
            order_index=order_index,
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)
        return material

    def get_material(self, material_id: str) -> TaskMaterial:
        material = self.db.query(TaskMaterial).filter(TaskMaterial.id == material_id).first()
        if not material:
            raise ResourceNotFoundError(f"Material {material_id} not found")
        return material

    def get_materials_by_task(self, task_id: str) -> List[TaskMaterial]:
        return (
            self.db.query(TaskMaterial)
            .filter(TaskMaterial.task_id == task_id)
            .order_by(TaskMaterial.order_index)
            .all()
        )

    def update_material(
        self,
        material_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        url: Optional[str] = None,
        file_path: Optional[str] = None,
        order_index: Optional[int] = None,
    ) -> TaskMaterial:
        material = self.get_material(material_id)

        if title is not None:
            material.title = title
        if content is not None:
            material.content = content
        if url is not None:
            material.url = url
        if file_path is not None:
            material.file_path = file_path
        if order_index is not None:
            material.order_index = order_index

        material.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(material)
        return material

    def delete_material(self, material_id: str) -> bool:
        material = self.get_material(material_id)
        self.db.delete(material)
        self.db.commit()
        return True

    def reorder_materials(self, task_id: str, material_ids: List[str]) -> List[TaskMaterial]:
        for index, material_id in enumerate(material_ids):
            material = self.get_material(material_id)
            if material.task_id != task_id:
                raise PermissionDeniedError(f"Material {material_id} does not belong to task {task_id}")
            material.order_index = index
            material.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        return self.get_materials_by_task(task_id)
