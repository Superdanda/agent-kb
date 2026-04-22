from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from app.repositories.learning_repo import LearningRepository
from app.repositories.post_repo import PostRepository
from app.models.learning_record import LearningRecord
from app.api.schemas.learning import LearningSubmit
from app.core.exceptions import ResourceNotFoundError


class LearningService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = LearningRepository(db)
        self.post_repo = PostRepository(db)

    def submit_learning(
        self, learner_agent_id: str, post_id: str, data: LearningSubmit
    ) -> LearningRecord:
        version = self.post_repo.get_version_by_id(data.version_id)
        if not version:
            raise ResourceNotFoundError(f"Version {data.version_id} not found")

        if version.post_id != post_id:
            raise ResourceNotFoundError(f"Version {data.version_id} does not belong to post {post_id}")

        record = self.repo.create_or_update(
            learner_agent_id=learner_agent_id,
            post_id=post_id,
            learned_version_id=data.version_id,
            learned_version_no=version.version_no,
            learn_note=data.learn_note,
        )
        return record

    def get_my_records(
        self,
        agent_id: str,
        status: Optional[str] = None,
        only_outdated: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[LearningRecord], int]:
        records, total = self.repo.get_list(
            learner_agent_id=agent_id,
            status=status,
            only_outdated=only_outdated,
            page=page,
            size=size,
        )
        for record in records:
            post = self.post_repo.get_by_id(record.post_id)
            if post:
                record.post_title = post.title
                version = self.post_repo.get_version_by_id(record.learned_version_id)
                if version:
                    record.version_no = version.version_no
        return records, total

    def get_all_records(
        self,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[LearningRecord], int]:
        records, total = self.repo.get_list(
            learner_agent_id=None,
            status=status,
            only_outdated=False,
            page=page,
            size=size,
        )
        for record in records:
            post = self.post_repo.get_by_id(record.post_id)
            if post:
                record.post_title = post.title
                version = self.post_repo.get_version_by_id(record.learned_version_id)
                if version:
                    record.version_no = version.version_no
        return records, total
