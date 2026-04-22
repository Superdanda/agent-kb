from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.skill import Skill, SkillStatus
from app.models.skill_version import SkillVersion, SkillVersionStatus


class SkillRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_skill(self, skill: Skill) -> Skill:
        self.db.add(skill)
        self.db.commit()
        self.db.refresh(skill)
        return skill

    def update_skill(self, skill: Skill) -> Skill:
        self.db.commit()
        self.db.refresh(skill)
        return skill

    def create_version(self, version: SkillVersion) -> SkillVersion:
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def update_version(self, version: SkillVersion) -> SkillVersion:
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_skill_by_id(self, skill_id: str, include_hidden: bool = False) -> Skill | None:
        query = (
            self.db.query(Skill)
            .options(joinedload(Skill.uploader_agent))
            .filter(Skill.id == skill_id)
        )
        if not include_hidden:
            query = query.filter(Skill.status == SkillStatus.ACTIVE)
        return query.first()

    def get_skill_by_slug(self, slug: str, include_hidden: bool = True) -> Skill | None:
        query = (
            self.db.query(Skill)
            .options(joinedload(Skill.uploader_agent))
            .filter(Skill.slug == slug)
        )
        if not include_hidden:
            query = query.filter(Skill.status == SkillStatus.ACTIVE)
        return query.first()

    def get_version_by_id(self, version_id: str) -> SkillVersion | None:
        return (
            self.db.query(SkillVersion)
            .options(joinedload(SkillVersion.created_by_agent), joinedload(SkillVersion.skill))
            .filter(SkillVersion.id == version_id)
            .first()
        )

    def get_version_by_skill_and_version(self, skill_id: str, version: str) -> SkillVersion | None:
        return (
            self.db.query(SkillVersion)
            .filter(
                SkillVersion.skill_id == skill_id,
                SkillVersion.version == version,
            )
            .first()
        )

    def list_skills(
        self,
        keyword: Optional[str] = None,
        tags: Optional[List[str]] = None,
        uploader_agent_id: Optional[str] = None,
        recommended_only: bool = False,
        official_only: bool = False,
        important_only: bool = False,
        status_value: Optional[str] = None,
        include_hidden: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> List[Skill]:
        query = self.db.query(Skill).options(joinedload(Skill.uploader_agent))
        if not include_hidden:
            query = query.filter(Skill.status == SkillStatus.ACTIVE)
        elif status_value:
            query = query.filter(Skill.status == status_value)
        if keyword:
            query = query.filter(
                or_(
                    Skill.name.ilike(f"%{keyword}%"),
                    Skill.slug.ilike(f"%{keyword}%"),
                    Skill.summary.ilike(f"%{keyword}%"),
                )
            )
        if tags:
            for tag in tags:
                query = query.filter(Skill.tags_json.contains(tag))
        if uploader_agent_id:
            query = query.filter(Skill.uploader_agent_id == uploader_agent_id)
        if recommended_only:
            query = query.filter(Skill.is_recommended.is_(True))
        if official_only:
            query = query.filter(Skill.is_official.is_(True))
        if important_only:
            query = query.filter(Skill.is_important.is_(True))

        query = query.order_by(
            Skill.is_official.desc(),
            Skill.is_important.desc(),
            Skill.is_recommended.desc(),
            Skill.updated_at.desc(),
        )
        return query.offset((page - 1) * size).limit(size).all()

    def count_skills(
        self,
        keyword: Optional[str] = None,
        tags: Optional[List[str]] = None,
        uploader_agent_id: Optional[str] = None,
        recommended_only: bool = False,
        official_only: bool = False,
        important_only: bool = False,
        status_value: Optional[str] = None,
        include_hidden: bool = False,
    ) -> int:
        query = self.db.query(Skill)
        if not include_hidden:
            query = query.filter(Skill.status == SkillStatus.ACTIVE)
        elif status_value:
            query = query.filter(Skill.status == status_value)
        if keyword:
            query = query.filter(
                or_(
                    Skill.name.ilike(f"%{keyword}%"),
                    Skill.slug.ilike(f"%{keyword}%"),
                    Skill.summary.ilike(f"%{keyword}%"),
                )
            )
        if tags:
            for tag in tags:
                query = query.filter(Skill.tags_json.contains(tag))
        if uploader_agent_id:
            query = query.filter(Skill.uploader_agent_id == uploader_agent_id)
        if recommended_only:
            query = query.filter(Skill.is_recommended.is_(True))
        if official_only:
            query = query.filter(Skill.is_official.is_(True))
        if important_only:
            query = query.filter(Skill.is_important.is_(True))
        return query.count()

    def list_versions(self, skill_id: str, include_hidden: bool = False) -> List[SkillVersion]:
        query = (
            self.db.query(SkillVersion)
            .options(joinedload(SkillVersion.created_by_agent))
            .filter(SkillVersion.skill_id == skill_id)
        )
        if not include_hidden:
            query = query.filter(SkillVersion.status == SkillVersionStatus.ACTIVE)
        return query.order_by(SkillVersion.created_at.desc()).all()
