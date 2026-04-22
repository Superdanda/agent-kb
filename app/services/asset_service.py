import uuid
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from fastapi import UploadFile

from app.core.file_storage import (
    build_dated_object_key,
    download_bytes_from_storage,
    read_upload_buffer,
    upload_bytes_to_storage,
    validate_standard_upload,
)
from app.repositories.asset_repo import AssetRepository
from app.models.post_asset import PostAsset, ScanStatus
from app.core.exceptions import ResourceNotFoundError


class AssetService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AssetRepository(db)

    def upload_asset(
        self,
        uploader_agent_id: str,
        post_id: str,
        version_id: Optional[str],
        file: UploadFile,
    ) -> PostAsset:
        upload = read_upload_buffer(file)
        magic_type = validate_standard_upload(upload)

        existing = self.repo.get_by_sha256(upload.sha256)
        if existing:
            return existing

        object_key = build_dated_object_key(
            "hermes-kb/post-assets",
            upload.original_filename,
            sha256_value=upload.sha256,
        )
        upload_bytes_to_storage(
            object_key=object_key,
            data=upload.contents,
            content_type=upload.content_type,
        )

        asset = PostAsset(
            id=str(uuid.uuid4()),
            post_id=post_id,
            version_id=version_id,
            original_filename=upload.original_filename,
            stored_object_key=object_key,
            file_ext=upload.file_ext,
            file_size=len(upload.contents),
            sha256=upload.sha256,
            mime_type=upload.content_type,
            detected_type=magic_type,
            scan_status=ScanStatus.SAFE,
            created_by_agent_id=uploader_agent_id,
        )
        return self.repo.create(asset)

    def download_asset(
        self, asset_id: str, downloader_agent_id: str
    ) -> Tuple[bytes, str, str]:
        asset = self.repo.get_by_id(asset_id)
        if not asset:
            raise ResourceNotFoundError(f"Asset {asset_id} not found")

        data = download_bytes_from_storage(object_key=asset.stored_object_key)
        return data, asset.original_filename, asset.mime_type

    def get_asset(self, asset_id: str) -> PostAsset:
        asset = self.repo.get_by_id(asset_id)
        if not asset:
            raise ResourceNotFoundError(f"Asset {asset_id} not found")
        return asset

    def get_post_assets(self, post_id: str, version_id: Optional[str] = None):
        return self.repo.get_by_post(post_id, version_id)
