import io
from datetime import datetime, timezone

import pytest
from fastapi import UploadFile

from app.core.exceptions import FileValidationError, StorageError, ValidationError
from app.core.file_storage import (
    build_dated_object_key,
    download_bytes_from_storage,
    read_upload_buffer,
    upload_bytes_to_storage,
    validate_standard_upload,
    validate_zip_upload,
)


def make_upload(filename: str, content: bytes, content_type: str = "application/octet-stream") -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content), headers={"content-type": content_type})


def test_read_upload_buffer_extracts_metadata():
    upload = read_upload_buffer(make_upload("guide.pdf", b"%PDF-1.7", "application/pdf"))

    assert upload.original_filename == "guide.pdf"
    assert upload.file_ext == ".pdf"
    assert upload.content_type == "application/pdf"
    assert upload.contents == b"%PDF-1.7"
    assert len(upload.sha256) == 64


def test_validate_standard_upload_accepts_pdf():
    upload = read_upload_buffer(make_upload("guide.pdf", b"%PDF-1.7"))

    detected_type = validate_standard_upload(upload)

    assert detected_type == "pdf"


def test_validate_standard_upload_rejects_unknown_magic_for_text():
    upload = read_upload_buffer(make_upload("notes.txt", b"plain text"))

    with pytest.raises(FileValidationError, match="unknown format"):
        validate_standard_upload(upload)


def test_validate_zip_upload_requires_zip_extension():
    upload = read_upload_buffer(make_upload("skill.md", b"not-a-zip"))

    with pytest.raises(ValidationError, match="Only zip skill packages are supported"):
        validate_zip_upload(upload)


def test_build_dated_object_key_keeps_prefix_hash_and_extension():
    object_key = build_dated_object_key(
        "hermes-kb/post-assets",
        "guide.pdf",
        now=datetime(2026, 4, 22, tzinfo=timezone.utc),
        sha256_value="abc123",
    )

    assert object_key == "hermes-kb/post-assets/2026/04/22/abc123.pdf"


def test_upload_and_download_helpers_use_storage_client(monkeypatch):
    calls: list[tuple[str, str, bytes, str]] = []

    class FakeStorageClient:
        def upload_bytes(self, bucket: str, object_key: str, data: bytes, content_type: str) -> str:
            calls.append((bucket, object_key, data, content_type))
            return f"/mock/{bucket}/{object_key}"

        def download_file(self, bucket: str, object_key: str, file_path: str) -> None:
            with open(file_path, "wb") as handle:
                handle.write(b"payload")

    monkeypatch.setattr(
        "app.core.file_storage.StorageClientFactory.get_client",
        lambda: FakeStorageClient(),
    )

    file_url = upload_bytes_to_storage(
        object_key="skills/pkg.zip",
        data=b"payload",
        content_type="application/zip",
    )
    downloaded = download_bytes_from_storage(object_key="skills/pkg.zip")

    assert file_url == "/mock/hermes-kb/skills/pkg.zip"
    assert downloaded == b"payload"
    assert calls == [("hermes-kb", "skills/pkg.zip", b"payload", "application/zip")]


def test_upload_bytes_to_storage_wraps_errors(monkeypatch):
    class BrokenStorageClient:
        def upload_bytes(self, bucket: str, object_key: str, data: bytes, content_type: str) -> str:
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "app.core.file_storage.StorageClientFactory.get_client",
        lambda: BrokenStorageClient(),
    )

    with pytest.raises(StorageError, match="Failed to upload file: boom"):
        upload_bytes_to_storage(
            object_key="skills/pkg.zip",
            data=b"payload",
            content_type="application/zip",
        )
