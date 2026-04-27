import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.file_storage import get_default_bucket, read_upload_buffer, upload_bytes_to_storage
from app.modules.task_board.models.task_material import TaskMaterial, MaterialType
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError
from app.modules.task_board.models.task import Task


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
        is_result: bool = False,
    ) -> TaskMaterial:
        self.ensure_task_exists(task_id)
        material = TaskMaterial(
            id=str(uuid.uuid4()),
            task_id=task_id,
            material_type=material_type,
            title=title,
            content=content,
            url=url,
            file_path=file_path,
            order_index=order_index,
            is_result=is_result,
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

    def ensure_task_exists(self, task_id: str) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")
        return task

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
        self.ensure_task_exists(task_id)
        for index, material_id in enumerate(material_ids):
            material = self.get_material(material_id)
            if material.task_id != task_id:
                raise PermissionDeniedError(f"Material {material_id} does not belong to task {task_id}")
            material.order_index = index
            material.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        return self.get_materials_by_task(task_id)

    def upload_file_material(
        self,
        task_id: str,
        title: str,
        file: UploadFile,
        material_type: MaterialType = MaterialType.FILE,
        is_result: bool = False,
    ) -> TaskMaterial:
        upload = read_upload_buffer(file)
        object_suffix = upload.file_ext or ""
        object_key = f"task_materials/{task_id}/{uuid.uuid4()}{object_suffix}"
        file_url = upload_bytes_to_storage(
            bucket=get_default_bucket(),
            object_key=object_key,
            data=upload.contents,
            content_type=upload.content_type,
        )
        return self.create_material(
            task_id=task_id,
            material_type=material_type,
            title=title,
            file_path=object_key,
            url=file_url,
            is_result=is_result,
        )

    def upload_bytes_material(
        self,
        task_id: str,
        title: str,
        filename: str,
        contents: bytes,
        content_type: str = "application/octet-stream",
        material_type: MaterialType = MaterialType.FILE,
        is_result: bool = False,
    ) -> TaskMaterial:
        self.ensure_task_exists(task_id)
        object_suffix = ""
        if "." in filename:
            object_suffix = "." + filename.rsplit(".", 1)[-1].lower()
        object_key = f"task_materials/{task_id}/{uuid.uuid4()}{object_suffix}"
        file_url = upload_bytes_to_storage(
            bucket=get_default_bucket(),
            object_key=object_key,
            data=contents,
            content_type=content_type,
        )
        return self.create_material(
            task_id=task_id,
            material_type=material_type,
            title=title,
            file_path=object_key,
            url=file_url,
            is_result=is_result,
        )
