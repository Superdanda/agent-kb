import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from app.repositories.post_repo import PostRepository
from app.repositories.learning_repo import LearningRepository
from app.models.post import Post, PostStatus, PostVisibility
from app.models.post_version import PostVersion, ChangeType
from app.api.schemas.post import PostCreate, PostUpdate
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError


class PostService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PostRepository(db)
        self.learning_repo = LearningRepository(db)

    def create_post(
        self, author_agent_id: str, author_name: str, data: PostCreate
    ) -> Post:
        post = Post(
            id=str(uuid.uuid4()),
            author_agent_id=author_agent_id,
            title=data.title,
            summary=data.summary,
            current_version_no=1,
            visibility=PostVisibility(data.visibility) if data.visibility else PostVisibility.PUBLIC_INTERNAL,
            status=PostStatus(data.status) if data.status else PostStatus.DRAFT,
            tags_json=data.tags or [],
        )
        post = self.repo.create(post)

        version = PostVersion(
            id=str(uuid.uuid4()),
            post_id=post.id,
            version_no=1,
            title_snapshot=data.title,
            summary_snapshot=data.summary,
            content_md=data.content_md,
            change_type=ChangeType.MINOR,
            change_note="Initial version",
            created_by_agent_id=author_agent_id,
        )
        version = self.repo.create_version(version)

        post.latest_version_id = version.id
        post = self.repo.update(post)

        post.author_name = author_name
        return post

    def update_post(
        self,
        post_id: str,
        agent_id: str,
        data: PostUpdate,
    ) -> Post:
        post = self.repo.get_by_id(post_id)
        if not post:
            raise ResourceNotFoundError(f"Post {post_id} not found")

        if post.author_agent_id != agent_id:
            raise PermissionDeniedError("Only the author can update the post")

        if data.title is not None:
            post.title = data.title
        if data.summary is not None:
            post.summary = data.summary
        if data.visibility is not None:
            post.visibility = PostVisibility(data.visibility)
        if data.status is not None:
            post.status = PostStatus(data.status)
        if data.tags is not None:
            post.tags_json = data.tags

        is_major = data.change_type == "MAJOR"

        if data.title is not None or data.content_md is not None or data.summary is not None:
            new_version_no = post.current_version_no + 1
            version = PostVersion(
                id=str(uuid.uuid4()),
                post_id=post.id,
                version_no=new_version_no,
                title_snapshot=data.title or post.title,
                summary_snapshot=data.summary if data.summary is not None else post.summary,
                content_md=data.content_md,
                change_type=ChangeType.MAJOR if is_major else ChangeType.MINOR,
                change_note=data.change_note,
                created_by_agent_id=agent_id,
            )
            version = self.repo.create_version(version)

            post.current_version_no = new_version_no
            post.latest_version_id = version.id

            if is_major:
                self.learning_repo.mark_outdated(post.id, new_version_no)

        post.updated_at = datetime.now(timezone.utc)
        post = self.repo.update(post)

        if post.author:
            post.author_name = post.author.name
        return post

    def get_post(
        self, post_id: str, learner_agent_id: Optional[str] = None
    ) -> Post:
        post = self.repo.get_by_id(post_id)
        if not post:
            raise ResourceNotFoundError(f"Post {post_id} not found")

        version_count = self.repo.get_version_count(post_id)
        post.version_count = version_count

        if post.author:
            post.author_name = post.author.name

        learning_record = None
        if learner_agent_id:
            learning_record = self.learning_repo.get_by_learner_post(
                learner_agent_id, post_id
            )
        if learning_record:
            post.learning_status = learning_record.status.value
        else:
            post.learning_status = None

        return post

    def get_posts(
        self,
        keyword: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author_agent_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Post], int]:
        posts = self.repo.get_list(
            keyword=keyword,
            tags=tags,
            author_agent_id=author_agent_id,
            status=status,
            page=page,
            size=size,
        )
        total = self.repo.count(
            keyword=keyword,
            tags=tags,
            author_agent_id=author_agent_id,
            status=status,
        )

        for post in posts:
            if post.author:
                post.author_name = post.author.name

        return posts, total

    def get_my_posts(
        self, agent_id: str, page: int = 1, size: int = 20
    ) -> Tuple[List[Post], int]:
        return self.get_posts(author_agent_id=agent_id, page=page, size=size)

    def get_post_versions(self, post_id: str) -> List[PostVersion]:
        post = self.repo.get_by_id(post_id)
        if not post:
            raise ResourceNotFoundError(f"Post {post_id} not found")

        versions = self.repo.get_versions_by_post_id(post_id)
        for v in versions:
            if v.created_by_agent:
                v.author_name = v.created_by_agent.name
        return versions

    def update_post_metadata(
        self, post_id: str, agent_id: str, data: PostUpdate
    ) -> Post:
        post = self.repo.get_by_id(post_id)
        if not post:
            raise ResourceNotFoundError(f"Post {post_id} not found")

        if post.author_agent_id != agent_id:
            raise PermissionDeniedError("Only the author can update the post")

        if data.title is not None:
            post.title = data.title
        if data.summary is not None:
            post.summary = data.summary
        if data.visibility is not None:
            post.visibility = PostVisibility(data.visibility)
        if data.status is not None:
            post.status = PostStatus(data.status)
        if data.tags is not None:
            post.tags_json = data.tags

        post.updated_at = datetime.now(timezone.utc)
        post = self.repo.update(post)

        if post.author:
            post.author_name = post.author.name
        return post
