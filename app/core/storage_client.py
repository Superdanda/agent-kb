from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import os
import shutil

from app.core.config import settings


class StorageClient(ABC):
    """Abstract base class for storage clients."""

    @abstractmethod
    def upload_file(self, bucket: str, object_key: str, file_path: str, content_type: str) -> str:
        pass

    @abstractmethod
    def upload_bytes(self, bucket: str, object_key: str, data: bytes, content_type: str) -> str:
        pass

    @abstractmethod
    def download_file(self, bucket: str, object_key: str, file_path: str) -> None:
        pass

    @abstractmethod
    def delete_file(self, bucket: str, object_key: str) -> None:
        pass

    @abstractmethod
    def get_file_url(self, bucket: str, object_key: str, expires: int = 3600) -> str:
        pass


class LocalStorageClient(StorageClient):
    """Local filesystem storage implementation."""

    def __init__(self):
        self.base_path = settings.LOCAL_STORAGE_PATH

    def _get_full_path(self, bucket: str, object_key: str) -> Path:
        return Path(self.base_path) / bucket / object_key

    def upload_file(self, bucket: str, object_key: str, file_path: str, content_type: str) -> str:
        full_path = self._get_full_path(bucket, object_key)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, full_path)
        return self.get_file_url(bucket, object_key)

    def upload_bytes(self, bucket: str, object_key: str, data: bytes, content_type: str) -> str:
        full_path = self._get_full_path(bucket, object_key)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)
        return self.get_file_url(bucket, object_key)

    def download_file(self, bucket: str, object_key: str, file_path: str) -> None:
        full_path = self._get_full_path(bucket, object_key)
        dest = Path(file_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(full_path, dest)

    def delete_file(self, bucket: str, object_key: str) -> None:
        full_path = self._get_full_path(bucket, object_key)
        if full_path.exists():
            full_path.unlink()

    def get_file_url(self, bucket: str, object_key: str, expires: int = 3600) -> str:
        return f"/data/file/{bucket}/{object_key}"


class MinioStorageClient(StorageClient):
    """MinIO storage implementation wrapping existing minio_client code."""

    def __init__(self) -> None:
        from io import BytesIO
        from minio import Minio

        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
        self._default_bucket = settings.MINIO_BUCKET

    def upload_file(self, bucket: str, object_key: str, file_path: str, content_type: str) -> str:
        with open(file_path, "rb") as f:
            data = f.read()
        return self.upload_bytes(bucket, object_key, data, content_type)

    def upload_bytes(self, bucket: str, object_key: str, data: bytes, content_type: str) -> str:
        from io import BytesIO
        self._ensure_bucket_exists(bucket)
        self._client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return self.get_file_url(bucket, object_key)

    def download_file(self, bucket: str, object_key: str, file_path: str) -> None:
        self._client.fget_object(bucket_name=bucket, object_name=object_key, file_path=file_path)

    def delete_file(self, bucket: str, object_key: str) -> None:
        self._client.remove_object(bucket_name=bucket, object_name=object_key)

    def get_file_url(self, bucket: str, object_key: str, expires: int = 3600) -> str:
        return self._client.presigned_get_object(bucket_name=bucket, object_name=object_key, expires=expires)

    def _ensure_bucket_exists(self, bucket: str) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)


class StorageClientFactory:
    """Factory to get storage client based on configuration."""

    @staticmethod
    def get_client() -> StorageClient:
        if settings.STORAGE_TYPE == "MINIO":
            return MinioStorageClient()
        return LocalStorageClient()


def get_storage_client() -> StorageClient:
    """Convenience function to get the configured storage client."""
    return StorageClientFactory.get_client()


storage_client = get_storage_client()
