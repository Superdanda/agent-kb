from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AssetUploadResponse(BaseModel):
    id: str
    original_filename: str
    file_ext: str
    file_size: int
    sha256: str
    scan_status: str
    stored_object_key: str
    mime_type: str

    model_config = {"from_attributes": True}


class AssetResponse(BaseModel):
    id: str
    post_id: str
    version_id: Optional[str]
    original_filename: str
    stored_object_key: str
    file_ext: str
    file_size: int
    sha256: str
    mime_type: str
    detected_type: str
    scan_status: str
    reject_reason: Optional[str]
    created_by_agent_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
