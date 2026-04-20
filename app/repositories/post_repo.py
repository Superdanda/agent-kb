import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.post import Post, PostStatus, PostVisibility
from app.models.post_version import PostVersion, ChangeType


class PostRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, post: Post) -> Post:
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return post

    def get_by_id(self, id: str) -> Post | None:
        return (
            self.db.query(Post)
            .options(joinedload(Post.author))
            .filter(Post.id == id)
            .first()
        )

    def update(self, post: Post) -> Post:
        self.db.commit()
        self.db.refresh(post)
        return post

    def create_version(self, version: PostVersion) -> PostVersion:
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def update_post_version(self, version: PostVersion) -> PostVersion:
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_list(
        self,
        keyword: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author_agent_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> List[Post]:
        query = self.db.query(Post).options(joinedload(Post.author))

        if keyword:
            query = query.filter(
                or_(
                    Post.title.ilike(f"%{keyword}%"),
                    Post.summary.ilike(f"%{keyword}%"),
                )
            )

        if tags:
            for tag in tags:
                query = query.filter(Post.tags_json.contains(tag))

        if author_agent_id:
            query = query.filter(Post.author_agent_id == author_agent_id)

        if status:
            query = query.filter(Post.status == status)

        query = query.order_by(Post.updated_at.desc())
        offset = (page - 1) * size
        return query.offset(offset).limit(size).all()

    def count(
        self,
        keyword: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author_agent_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        query = self.db.query(Post)

        if keyword:
            query = query.filter(
                or_(
                    Post.title.ilike(f"%{keyword}%"),
                    Post.summary.ilike(f"%{keyword}%"),
                )
            )

        if tags:
            for tag in tags:
                query = query.filter(Post.tags_json.contains(tag))

        if author_agent_id:
            query = query.filter(Post.author_agent_id == author_agent_id)

        if status:
            query = query.filter(Post.status == status)

        return query.count()

    def get_versions_by_post_id(self, post_id: str) -> List[PostVersion]:
        return (
            self.db.query(PostVersion)
            .options(joinedload(PostVersion.created_by_agent))
            .filter(PostVersion.post_id == post_id)
            .order_by(PostVersion.version_no.desc())
            .all()
        )

    def get_version_by_id(self, version_id: str) -> PostVersion | None:
        return (
            self.db.query(PostVersion)
            .options(joinedload(PostVersion.created_by_agent))
            .filter(PostVersion.id == version_id)
            .first()
        )

    def get_latest_version(self, post_id: str) -> PostVersion | None:
        return (
            self.db.query(PostVersion)
            .filter(PostVersion.post_id == post_id)
            .order_by(PostVersion.version_no.desc())
            .first()
        )

    def get_version_count(self, post_id: str) -> int:
        return self.db.query(PostVersion).filter(PostVersion.post_id == post_id).count()
