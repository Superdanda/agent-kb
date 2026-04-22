import os
import re
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

import yaml
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.file_storage import (
    download_bytes_from_storage,
    read_upload_buffer,
    upload_bytes_to_storage,
    validate_zip_upload,
)
from app.core.exceptions import (
    AlreadyExistsError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from app.models.skill import Skill, SkillStatus
from app.models.skill_version import SkillVersion, SkillVersionStatus
from app.repositories.skill_repo import SkillRepository

MAX_TAGS = 10
TAG_PATTERN = re.compile(r"^[a-z0-9-]{1,20}$")


def _version_key(version: str) -> tuple:
    parts = re.findall(r"[0-9]+|[A-Za-z]+", version)
    normalized = []
    for part in parts:
        if part.isdigit():
            normalized.append((0, int(part)))
        else:
            normalized.append((1, part.lower()))
    return tuple(normalized)


class SkillService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SkillRepository(db)

    def upload_skill_package(
        self,
        file: UploadFile,
        uploader_agent_id: Optional[str] = None,
        uploader_admin_uuid: Optional[str] = None,
        release_note: Optional[str] = None,
    ) -> Tuple[Skill, SkillVersion]:
        if not uploader_agent_id and not uploader_admin_uuid:
            raise ValidationError("Uploader is required")
        upload = read_upload_buffer(file)
        validate_zip_upload(upload)

        metadata, package_filename = self._parse_skill_package(upload.contents)
        if release_note:
            metadata["release_note"] = release_note.strip()

        skill = self.repo.get_skill_by_slug(metadata["slug"], include_hidden=True)
        if skill and self.repo.get_version_by_skill_and_version(skill.id, metadata["version"]):
            raise AlreadyExistsError(
                f"Skill {metadata['slug']} version {metadata['version']} already exists"
            )
        if skill:
            if uploader_agent_id:
                if skill.uploader_agent_id != uploader_agent_id or skill.uploader_admin_uuid:
                    raise PermissionDeniedError("Only the original uploader can publish new versions")
            elif uploader_admin_uuid:
                if skill.uploader_admin_uuid != uploader_admin_uuid or skill.uploader_agent_id:
                    raise PermissionDeniedError("Only the original uploader can publish new versions")

        now = datetime.now(timezone.utc)
        object_key = (
            f"hermes-kb/skills/{now.year}/{now.month:02d}/{now.day:02d}/"
            f"{metadata['slug']}/{metadata['version']}/{upload.sha256}.zip"
        )
        upload_bytes_to_storage(
            object_key=object_key,
            data=upload.contents,
            content_type=upload.content_type or "application/zip",
            failure_message="Failed to upload skill package",
        )

        if not skill:
            skill = Skill(
                id=str(uuid.uuid4()),
                slug=metadata["slug"],
                name=metadata["name"],
                summary=metadata["summary"],
                tags_json=metadata["tags"],
                uploader_agent_id=uploader_agent_id,
                uploader_admin_uuid=uploader_admin_uuid,
                status=SkillStatus.ACTIVE,
            )
            skill = self.repo.create_skill(skill)
        else:
            skill.name = metadata["name"]
            skill.summary = metadata["summary"]
            skill.tags_json = metadata["tags"]
            skill.updated_at = now
            skill = self.repo.update_skill(skill)

        version = SkillVersion(
            id=str(uuid.uuid4()),
            skill_id=skill.id,
            version=metadata["version"],
            summary_snapshot=metadata["summary"],
            tags_snapshot=metadata["tags"],
            release_note=metadata.get("release_note"),
            package_filename=package_filename,
            stored_object_key=object_key,
            file_size=len(upload.contents),
            sha256=upload.sha256,
            mime_type=upload.content_type or "application/zip",
            metadata_json=metadata,
            created_by_agent_id=uploader_agent_id,
            created_by_admin_uuid=uploader_admin_uuid,
            status=SkillVersionStatus.ACTIVE,
        )
        version = self.repo.create_version(version)

        current_version = self.get_current_version(skill)
        if not current_version or _version_key(version.version) >= _version_key(current_version.version):
            skill.current_version_id = version.id
        skill.updated_at = now
        skill = self.repo.update_skill(skill)

        self._attach_skill_view(skill, include_hidden_versions=False)
        version.uploader_name = self._resolve_uploader_name(version.created_by_agent, version.created_by_admin_uuid)
        return skill, version

    def list_skills(
        self,
        keyword: Optional[str] = None,
        tags: Optional[list[str]] = None,
        uploader_agent_id: Optional[str] = None,
        recommended_only: bool = False,
        official_only: bool = False,
        important_only: bool = False,
        status_value: Optional[str] = None,
        include_hidden: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[list[Skill], int]:
        normalized_tags = self._normalize_tags(tags or []) if tags else None
        skills = self.repo.list_skills(
            keyword=keyword,
            tags=normalized_tags,
            uploader_agent_id=uploader_agent_id,
            recommended_only=recommended_only,
            official_only=official_only,
            important_only=important_only,
            status_value=status_value,
            include_hidden=include_hidden,
            page=page,
            size=size,
        )
        total = self.repo.count_skills(
            keyword=keyword,
            tags=normalized_tags,
            uploader_agent_id=uploader_agent_id,
            recommended_only=recommended_only,
            official_only=official_only,
            important_only=important_only,
            status_value=status_value,
            include_hidden=include_hidden,
        )
        for skill in skills:
            self._attach_skill_view(skill, include_hidden_versions=include_hidden)
        return skills, total

    def get_skill(self, skill_id: str, include_hidden: bool = False) -> Skill:
        skill = self.repo.get_skill_by_id(skill_id, include_hidden=include_hidden)
        if not skill:
            raise ResourceNotFoundError(f"Skill {skill_id} not found")
        self._attach_skill_view(skill, include_hidden_versions=include_hidden)
        return skill

    def get_skill_versions(self, skill_id: str, include_hidden: bool = False) -> list[SkillVersion]:
        skill = self.repo.get_skill_by_id(skill_id, include_hidden=True)
        if not skill:
            raise ResourceNotFoundError(f"Skill {skill_id} not found")
        versions = self.repo.list_versions(skill_id, include_hidden=include_hidden)
        for version in versions:
            version.uploader_name = self._resolve_uploader_name(version.created_by_agent, version.created_by_admin_uuid)
        return versions

    def download_skill_version(self, version_id: str) -> tuple[bytes, str, str]:
        version = self.repo.get_version_by_id(version_id)
        if (
            not version
            or version.status != SkillVersionStatus.ACTIVE
            or not version.skill
            or version.skill.status != SkillStatus.ACTIVE
        ):
            raise ResourceNotFoundError(f"Skill version {version_id} not found")
        return self._download_file(version.stored_object_key, version.package_filename, version.mime_type or "application/zip")

    def download_skill_latest(self, skill_id: str) -> tuple[bytes, str, str]:
        skill = self.get_skill(skill_id)
        if not skill.current_version:
            raise ResourceNotFoundError(f"Skill {skill_id} has no downloadable version")
        version = skill.current_version
        return self._download_file(version.stored_object_key, version.package_filename, version.mime_type or "application/zip")

    def check_update(self, slug: str, current_version: str) -> dict[str, Any]:
        skill = self.repo.get_skill_by_slug(slug, include_hidden=False)
        if not skill:
            raise ResourceNotFoundError(f"Skill {slug} not found")
        self._attach_skill_view(skill, include_hidden_versions=False)
        latest_version = skill.current_version.version if skill.current_version else None
        has_update = bool(latest_version and _version_key(latest_version) > _version_key(current_version))
        return {
            "slug": slug,
            "current_version": current_version,
            "latest_version": latest_version,
            "has_update": has_update,
            "download_url": f"/api/skills/{skill.id}/download" if latest_version else None,
            "skill_id": skill.id,
        }

    def update_skill_admin(self, skill_id: str, **kwargs: Any) -> Skill:
        skill = self.repo.get_skill_by_id(skill_id, include_hidden=True)
        if not skill:
            raise ResourceNotFoundError(f"Skill {skill_id} not found")

        if "is_recommended" in kwargs and kwargs["is_recommended"] is not None:
            skill.is_recommended = kwargs["is_recommended"]
        if "is_important" in kwargs and kwargs["is_important"] is not None:
            skill.is_important = kwargs["is_important"]
        if "is_official" in kwargs and kwargs["is_official"] is not None:
            skill.is_official = kwargs["is_official"]
        if "status" in kwargs and kwargs["status"]:
            skill.status = SkillStatus(kwargs["status"])

        skill.updated_at = datetime.now(timezone.utc)
        skill = self.repo.update_skill(skill)
        self._attach_skill_view(skill, include_hidden_versions=True)
        return skill

    def update_version_status(self, version_id: str, status: str) -> SkillVersion:
        version = self.repo.get_version_by_id(version_id)
        if not version:
            raise ResourceNotFoundError(f"Skill version {version_id} not found")
        version.status = SkillVersionStatus(status)
        version.updated_at = datetime.now(timezone.utc)
        version = self.repo.update_version(version)

        skill = self.repo.get_skill_by_id(version.skill_id, include_hidden=True)
        if skill:
            current_version = self.get_current_version(skill, include_hidden=False)
            skill.current_version_id = current_version.id if current_version else None
            skill.updated_at = datetime.now(timezone.utc)
            self.repo.update_skill(skill)
        version.uploader_name = self._resolve_uploader_name(version.created_by_agent, version.created_by_admin_uuid)
        return version

    def get_current_version(self, skill: Skill, include_hidden: bool = False) -> Optional[SkillVersion]:
        versions = self.repo.list_versions(skill.id, include_hidden=include_hidden)
        if not versions:
            return None
        versions = sorted(versions, key=lambda item: _version_key(item.version), reverse=True)
        return versions[0]

    def _attach_skill_view(self, skill: Skill, include_hidden_versions: bool) -> None:
        skill.version_items = self.get_skill_versions(skill.id, include_hidden=include_hidden_versions)
        skill.current_version = None
        for version in skill.version_items:
            if skill.current_version_id and version.id == skill.current_version_id:
                skill.current_version = version
                break
        if not skill.current_version:
            skill.current_version = self.get_current_version(skill, include_hidden=include_hidden_versions)
        skill.uploader_name = self._resolve_uploader_name(skill.uploader_agent, skill.uploader_admin_uuid)

    def _download_file(self, object_key: str, filename: str, mime_type: str) -> tuple[bytes, str, str]:
        data = download_bytes_from_storage(
            object_key=object_key,
            failure_message="Failed to download skill package",
        )
        return data, filename, mime_type

    def _parse_skill_package(self, contents: bytes) -> tuple[dict[str, Any], str]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        try:
            with zipfile.ZipFile(tmp_path, "r") as archive:
                skill_md_name = None
                metadata_name = None
                for info in archive.infolist():
                    base_name = Path(info.filename).name
                    if base_name == "SKILL.md":
                        skill_md_name = info.filename
                    if base_name in {"skill.yaml", "skill.yml"}:
                        metadata_name = info.filename

                if not skill_md_name:
                    raise ValidationError("Skill package must include SKILL.md")
                if not metadata_name:
                    raise ValidationError("Skill package must include skill.yaml")

                metadata = yaml.safe_load(archive.read(metadata_name)) or {}
                if not isinstance(metadata, dict):
                    raise ValidationError("skill.yaml must be a valid object")

                parsed = {
                    "name": str(metadata.get("name") or "").strip(),
                    "slug": str(metadata.get("slug") or metadata.get("id") or "").strip(),
                    "version": str(metadata.get("version") or "").strip(),
                    "summary": str(
                        metadata.get("summary")
                        or metadata.get("description")
                        or ""
                    ).strip(),
                    "tags": metadata.get("tags") or [],
                    "release_note": str(
                        metadata.get("release_note")
                        or metadata.get("change_log")
                        or metadata.get("changelog")
                        or ""
                    ).strip() or None,
                    "entry_files": {
                        "skill_md": skill_md_name,
                        "metadata": metadata_name,
                    },
                }
        finally:
            os.unlink(tmp_path)

        if not parsed["name"]:
            raise ValidationError("skill.yaml name is required")
        if not parsed["slug"]:
            raise ValidationError("skill.yaml slug is required")
        if not re.fullmatch(r"[a-z0-9-]{2,128}", parsed["slug"]):
            raise ValidationError("skill slug must use lowercase letters, numbers, or hyphens")
        if not parsed["version"]:
            raise ValidationError("skill.yaml version is required")
        parsed["tags"] = self._normalize_tags(parsed["tags"])
        return parsed, f"{parsed['slug']}-{parsed['version']}.zip"

    def _normalize_tags(self, tags: list[Any]) -> list[str]:
        if isinstance(tags, str):
            tags = [item.strip() for item in tags.split(",") if item.strip()]
        normalized: list[str] = []
        for tag in tags:
            value = str(tag).strip().lower()
            if not value:
                continue
            if not TAG_PATTERN.fullmatch(value):
                raise ValidationError(
                    "Tags must be lowercase and only contain letters, numbers, or hyphens"
                )
            if value not in normalized:
                normalized.append(value)
        if len(normalized) > MAX_TAGS:
            raise ValidationError(f"At most {MAX_TAGS} tags are allowed")
        return normalized

    def _resolve_uploader_name(self, agent: Any, admin_uuid: Optional[str]) -> str:
        if agent:
            return agent.name
        if admin_uuid:
            return f"admin:{admin_uuid[:8]}"
        return "unknown"
