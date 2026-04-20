import os
import uuid
import tempfile
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from fastapi import UploadFile

from app.repositories.asset_repo import AssetRepository
from app.models.post_asset import PostAsset, ScanStatus
from app.core.storage_client import StorageClientFactory
from app.core.security import sha256_bytes
from app.core.exceptions import ResourceNotFoundError, FileValidationError, StorageError
from app.utils.file_check import validate_extension, validate_magic_number, get_magic_type
from app.utils.zip_check import validate_zip_safety


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
        contents = file.file.read()
        original_filename = file.filename or "unknown"
        file_ext = os.path.splitext(original_filename.lower())[1]

        if not validate_extension(original_filename):
            raise FileValidationError(f"File extension not allowed: {file_ext}")

        is_valid_magic, magic_type = validate_magic_number(contents[:64])
        if not is_valid_magic:
            detected = magic_type if magic_type != "unknown" else "unknown format"
            raise FileValidationError(f"File magic number validation failed: {detected}")

        if file_ext == ".zip":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                tmp.write(contents)
                tmp_path = tmp.name
            try:
                is_safe, msg = validate_zip_safety(tmp_path)
                if not is_safe:
                    raise FileValidationError(f"ZIP validation failed: {msg}")
            finally:
                os.unlink(tmp_path)

        file_sha256 = sha256_bytes(contents)

        existing = self.repo.get_by_sha256(file_sha256)
        if existing:
            return existing

        now = datetime.now(timezone.utc)
        yyyy = now.year
        mm = now.month
        dd = now.day
        object_key = f"hermes-kb/post-assets/{yyyy}/{mm:02d}/{dd:02d}/{file_sha256}{file_ext}"

        content_type = file.content_type or "application/octet-stream"

        try:
            storage = StorageClientFactory.get_client()
            storage.upload_bytes(
                bucket="hermes-kb",
                object_key=object_key,
                data=contents,
                content_type=content_type,
            )
        except Exception as e:
            raise StorageError(f"Failed to upload file: {str(e)}")

        asset = PostAsset(
            id=str(uuid.uuid4()),
            post_id=post_id,
            version_id=version_id,
            original_filename=original_filename,
            stored_object_key=object_key,
            file_ext=file_ext,
            file_size=len(contents),
            sha256=file_sha256,
            mime_type=content_type,
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

        try:
            storage = StorageClientFactory.get_client()
            from pathlib import Path
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                storage.download_file(
                    bucket="hermes-kb",
                    object_key=asset.stored_object_key,
                    file_path=tmp.name,
                )
                data = Path(tmp.name).read_bytes()
            import os
            os.unlink(tmp.name)
        except Exception as e:
            raise StorageError(f"Failed to download file: {str(e)}")

        return data, asset.original_filename, asset.mime_type

    def get_asset(self, asset_id: str) -> PostAsset:
        asset = self.repo.get_by_id(asset_id)
        if not asset:
            raise ResourceNotFoundError(f"Asset {asset_id} not found")
        return asset

    def get_post_assets(self, post_id: str, version_id: Optional[str] = None):
        return self.repo.get_by_post(post_id, version_id)
