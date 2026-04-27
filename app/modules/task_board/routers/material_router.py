from typing import Optional, List

from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.modules.task_board.models.task_material import MaterialType
from app.modules.task_board.schemas.task_material import TaskMaterialResponse
from app.modules.task_board.services.material_service import MaterialService

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
    is_result: bool = False,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    material = MaterialService(db).create_material(
        task_id=task_id,
        material_type=material_type,
        title=title,
        content=content,
        url=url,
        file_path=file_path,
        order_index=order_index,
        is_result=is_result,
    )
    return TaskMaterialResponse.model_validate(material)


@router.get("/task/{task_id}")
def list_materials_by_task(
    task_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    materials = MaterialService(db).get_materials_by_task(task_id)
    return [TaskMaterialResponse.model_validate(m) for m in materials]


@router.get("/{material_id}")
def get_material(
    material_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    material = MaterialService(db).get_material(material_id)
    return TaskMaterialResponse.model_validate(material)


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
    material = MaterialService(db).update_material(
        material_id=material_id,
        title=title,
        content=content,
        url=url,
        file_path=file_path,
        order_index=order_index,
    )
    return TaskMaterialResponse.model_validate(material)


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    MaterialService(db).delete_material(material_id)
    return None


@router.post("/reorder")
def reorder_materials(
    task_id: str,
    material_ids: List[str],
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    materials = MaterialService(db).reorder_materials(task_id, material_ids)
    return [TaskMaterialResponse.model_validate(m) for m in materials]


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_material_file(
    task_id: str = Form(...),
    title: str = Form(...),
    material_type: MaterialType = Form(MaterialType.FILE),
    is_result: bool = Form(False),
    file: UploadFile = File(...),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Upload a file as task material and store in MinIO."""
    material = MaterialService(db).upload_file_material(
        task_id=task_id,
        title=title,
        material_type=material_type,
        file=file,
        is_result=is_result,
    )
    return TaskMaterialResponse.model_validate(material)
