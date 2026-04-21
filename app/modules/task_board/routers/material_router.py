import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.modules.task_board.models.task_material import TaskMaterial, MaterialType
from app.modules.task_board.models.task import Task

router = APIRouter(prefix="/materials", tags=["task_materials"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_material(
    task_id: str,
    material_type: MaterialType,
    title: str,
    content: Optional[str] = None,
    url: Optional[str] = None,
    file_path: Optional[str] = None,
    order_index: int = 0,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Task {task_id} not found")
    
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
    db.add(material)
    db.commit()
    db.refresh(material)
    
    return material


@router.get("/task/{task_id}")
def list_materials_by_task(
    task_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    materials = db.query(TaskMaterial).filter(
        TaskMaterial.task_id == task_id
    ).order_by(TaskMaterial.order_index).all()
    
    return materials


@router.get("/{material_id}")
def get_material(
    material_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    material = db.query(TaskMaterial).filter(TaskMaterial.id == material_id).first()
    if not material:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Material {material_id} not found")
    
    return material


@router.put("/{material_id}")
def update_material(
    material_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    url: Optional[str] = None,
    file_path: Optional[str] = None,
    order_index: Optional[int] = None,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    material = db.query(TaskMaterial).filter(TaskMaterial.id == material_id).first()
    if not material:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Material {material_id} not found")
    
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
    db.commit()
    db.refresh(material)
    
    return material


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    material = db.query(TaskMaterial).filter(TaskMaterial.id == material_id).first()
    if not material:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Material {material_id} not found")
    
    db.delete(material)
    db.commit()
    
    return None


@router.post("/reorder")
def reorder_materials(
    task_id: str,
    material_ids: List[str],
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Task {task_id} not found")
    
    # Update order for each material
    for index, material_id in enumerate(material_ids):
        material = db.query(TaskMaterial).filter(
            TaskMaterial.id == material_id,
            TaskMaterial.task_id == task_id,
        ).first()
        if material:
            material.order_index = index
            material.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    # Return updated materials
    materials = db.query(TaskMaterial).filter(
        TaskMaterial.task_id == task_id
    ).order_by(TaskMaterial.order_index).all()
    
    return materials
