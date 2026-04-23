from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import os
import uuid
import aiofiles

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.modules.task_board.models.task_material import TaskMaterial
from app.modules.task_board.models.task import Task
from app.utils.security_check import validate_file_bytes

router = APIRouter(prefix="/files", tags=["task_files"])

UPLOAD_DIR = "uploads/task_board"

@router.post("/upload/{task_id}")
async def upload_file(
    task_id: str,
    file: UploadFile = File(...),
    is_result: bool = False,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    # 验证任务存在
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 读取文件内容
    content = await file.read()
    
    # 安全检查
    result = validate_file_bytes(file.filename, content)
    if not result.is_safe:
        raise HTTPException(status_code=400, detail=result.message)
    
    # 生成存储路径
    material_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    filename = f"{material_id}{ext}"
    task_dir = os.path.join(UPLOAD_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)
    file_path = os.path.join(task_dir, filename)
    
    # 保存文件
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # 创建材料记录
    material = TaskMaterial(
        id=material_id,
        task_id=task_id,
        material_type="FILE",
        title=file.filename,
        file_path=file_path,
        is_result=is_result,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    
    return {"id": material.id, "filename": file.filename, "is_result": is_result}

@router.get("/download/{material_id}")
def download_file(
    material_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    material = db.query(TaskMaterial).filter(TaskMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if not material.file_path or not os.path.exists(material.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # 流式响应
    def iterfile():
        with open(material.file_path, 'rb') as f:
            while chunk := f.read(8192):
                yield chunk
    
    ext = os.path.splitext(material.file_path)[1]
    media_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.txt': 'text/plain',
        '.zip': 'application/zip',
    }
    
    return StreamingResponse(
        iterfile(),
        media_type=media_types.get(ext, 'application/octet-stream'),
        headers={"Content-Disposition": f"attachment; filename={material.title}"}
    )

@router.post("/mark-result/{material_id}")
def mark_as_result(
    material_id: str,
    is_result: bool = True,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    material = db.query(TaskMaterial).filter(TaskMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    material.is_result = is_result
    db.commit()
    
    return {"id": material.id, "is_result": material.is_result}
