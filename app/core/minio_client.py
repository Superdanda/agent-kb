from io import BytesIO
from pathlib import Path
from typing import Optional

from minio import Minio

from app.core.config import settings


class MinioClient:
    def __init__(self) -> None:
        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
        self._default_bucket = settings.MINIO_BUCKET

    @property
    def client(self) -> Minio:
        return self._client

    @property
    def default_bucket(self) -> str:
        return self._default_bucket

    def upload_file(
        self,
        bucket: str,
        object_key: str,
        file_path: str | Path,
        content_type: str | None = None,
    ) -> None:
        with open(file_path, "rb") as f:
            data = f.read()
        self.upload_bytes(bucket, object_key, data, content_type)

    def upload_bytes(
        self,
        bucket: str,
        object_key: str,
        data_bytes: bytes,
        content_type: str | None = None,
    ) -> None:
        self.ensure_bucket_exists(bucket)
        self._client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=BytesIO(data_bytes),
            length=len(data_bytes),
            content_type=content_type,
        )

    def download_file(self, bucket: str, object_key: str, file_path: str | Path) -> None:
        self._client.fget_object(bucket_name=bucket, object_name=object_key, file_path=str(file_path))

    def get_presigned_url(self, bucket: str, object_key: str, expires: int = 3600) -> str:
        return self._client.presigned_get_object(bucket_name=bucket, object_name=object_key, expires=expires)

    def delete_file(self, bucket: str, object_key: str) -> None:
        self._client.remove_object(bucket_name=bucket, object_name=object_key)

    def ensure_bucket_exists(self, bucket: str) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)


minio_client = MinioClient()
