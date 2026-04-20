from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from app.models.learning_record import LearningRecord, LearningStatus


class LearningRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_or_update(
        self,
        learner_agent_id: str,
        post_id: str,
        learned_version_id: str,
        learned_version_no: int,
        learn_note: Optional[str] = None,
    ) -> LearningRecord:
        existing = self.get_by_learner_post(learner_agent_id, post_id)
        if existing:
            existing.learned_version_id = learned_version_id
            existing.learned_version_no = learned_version_no
            existing.status = LearningStatus.LEARNED
            existing.learn_note = learn_note
            existing.learned_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            record = LearningRecord(
                learner_agent_id=learner_agent_id,
                post_id=post_id,
                learned_version_id=learned_version_id,
                learned_version_no=learned_version_no,
                status=LearningStatus.LEARNED,
                learn_note=learn_note,
                learned_at=datetime.now(timezone.utc),
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record

    def get_by_learner_post(
        self, learner_agent_id: str, post_id: str
    ) -> LearningRecord | None:
        return (
            self.db.query(LearningRecord)
            .filter(
                LearningRecord.learner_agent_id == learner_agent_id,
                LearningRecord.post_id == post_id,
            )
            .first()
        )

    def get_list(
        self,
        learner_agent_id: Optional[str] = None,
        status: Optional[str] = None,
        only_outdated: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[LearningRecord], int]:
        query = self.db.query(LearningRecord)

        if learner_agent_id:
            query = query.filter(LearningRecord.learner_agent_id == learner_agent_id)

        if status:
            query = query.filter(LearningRecord.status == status)

        if only_outdated:
            query = query.filter(LearningRecord.status == LearningStatus.OUTDATED)

        total = query.count()
        offset = (page - 1) * size
        records = query.order_by(LearningRecord.updated_at.desc()).offset(offset).limit(size).all()
        return records, total

    def mark_outdated(self, post_id: str, from_version_no: int) -> int:
        """Mark OUTDATED all LEARNED records where learned_version_no < from_version_no"""
        updated = (
            self.db.query(LearningRecord)
            .filter(
                LearningRecord.post_id == post_id,
                LearningRecord.status == LearningStatus.LEARNED,
                LearningRecord.learned_version_no < from_version_no,
            )
            .update({"status": LearningStatus.OUTDATED}, synchronize_session=False)
        )
        self.db.commit()
        return updated
