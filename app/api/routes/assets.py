from fastapi import APIRouter, Depends, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.api.schemas.asset import AssetUploadResponse, AssetResponse
from app.services.asset_service import AssetService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/upload", response_model=AssetUploadResponse)
def upload_asset(
    file: UploadFile = File(...),
    post_id: str = Form(...),
    version_id: Optional[str] = Form(None),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AssetService(db)
    asset = svc.upload_asset(agent_id, post_id, version_id, file)
    return asset


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AssetService(db)
    return svc.get_asset(asset_id)


@router.get("/{asset_id}/download")
def download_asset(
    asset_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AssetService(db)
    data, filename, mime_type = svc.download_asset(asset_id, agent_id)
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.get("/post/{post_id}/assets")
def post_assets(
    post_id: str,
    version_id: Optional[str] = None,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AssetService(db)
    assets = svc.get_post_assets(post_id, version_id)
    return {"items": assets}
