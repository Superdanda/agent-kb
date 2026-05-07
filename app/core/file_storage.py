import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Type

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import FileValidationError, StorageError, ValidationError
from app.core.security import sha256_bytes
from app.core.storage_client import StorageClientFactory
from app.core.file_security import (
    validate_extension,
    validate_magic_number,
    validate_zip_safety,
)

DEFAULT_STORAGE_BUCKET = "hermes-kb"


@dataclass(frozen=True)
class UploadBuffer:
    contents: bytes
    original_filename: str
    file_ext: str
    content_type: str
    sha256: str


def read_upload_buffer(file: UploadFile) -> UploadBuffer:
    original_filename = file.filename or "unknown"
    file_ext = os.path.splitext(original_filename.lower())[1]
    content_type = file.content_type or "application/octet-stream"
    contents = file.file.read()
    return UploadBuffer(
        contents=contents,
        original_filename=original_filename,
        file_ext=file_ext,
        content_type=content_type,
        sha256=sha256_bytes(contents),
    )


def validate_standard_upload(
    upload: UploadBuffer,
    *,
    error_cls: Type[Exception] = FileValidationError,
) -> str:
    if not validate_extension(upload.original_filename):
        raise error_cls(f"File extension not allowed: {upload.file_ext}")

    is_valid_magic, magic_type = validate_magic_number(upload.contents[:64])
    if not is_valid_magic:
        detected = magic_type if magic_type != "unknown" else "unknown format"
        raise error_cls(f"File magic number validation failed: {detected}")

    if upload.file_ext == ".zip":
        validate_zip_upload(
            upload,
            error_cls=error_cls,
            extension_checked=True,
            failure_message_prefix="ZIP validation failed",
        )

    return magic_type


def validate_zip_upload(
    upload: UploadBuffer,
    *,
    error_cls: Type[Exception] = ValidationError,
    extension_checked: bool = False,
    failure_message_prefix: str = "Invalid skill package",
) -> None:
    if not extension_checked and upload.file_ext != ".zip":
        raise error_cls("Only zip skill packages are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(upload.contents)
        tmp_path = tmp.name
    try:
        is_safe, message = validate_zip_safety(tmp_path)
        if not is_safe:
            raise error_cls(f"{failure_message_prefix}: {message}")
    finally:
        os.unlink(tmp_path)


def build_dated_object_key(
    prefix: str,
    filename: str,
    *,
    now: Optional[datetime] = None,
    sha256_value: Optional[str] = None,
) -> str:
    timestamp = now or datetime.now(timezone.utc)
    file_ext = os.path.splitext(filename.lower())[1]
    file_hash = sha256_value or sha256_bytes(filename.encode("utf-8"))
    return (
        f"{prefix}/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/"
        f"{file_hash}{file_ext}"
    )


def upload_bytes_to_storage(
    *,
    object_key: str,
    data: bytes,
    content_type: str,
    bucket: str = DEFAULT_STORAGE_BUCKET,
    failure_message: str = "Failed to upload file",
) -> str:
    try:
        storage = StorageClientFactory.get_client()
        return storage.upload_bytes(
            bucket=bucket,
            object_key=object_key,
            data=data,
            content_type=content_type,
        )
    except Exception as exc:
        raise StorageError(f"{failure_message}: {exc}") from exc


def download_bytes_from_storage(
    *,
    object_key: str,
    bucket: str = DEFAULT_STORAGE_BUCKET,
    failure_message: str = "Failed to download file",
) -> bytes:
    try:
        storage = StorageClientFactory.get_client()
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            storage.download_file(bucket=bucket, object_key=object_key, file_path=tmp.name)
            data = Path(tmp.name).read_bytes()
        os.unlink(tmp.name)
        return data
    except Exception as exc:
        raise StorageError(f"{failure_message}: {exc}") from exc


def get_default_bucket() -> str:
    return settings.MINIO_BUCKET or DEFAULT_STORAGE_BUCKET
