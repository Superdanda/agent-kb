import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.modules.task_board.models.task_rating import TaskRating, RatingDimension
from app.modules.task_board.models.task import Task, TaskStatus
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError, AlreadyExistsError


class RatingService:
    def __init__(self, db: Session):
        self.db = db

    def create_rating(
        self,
        task_id: str,
        rater_agent_id: str,
        rated_agent_id: str,
        dimension: RatingDimension,
        score: int,
        comment: Optional[str] = None,
    ) -> TaskRating:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ResourceNotFoundError(f"Task {task_id} not found")

        if task.status != TaskStatus.COMPLETED:
            raise PermissionDeniedError("Can only rate completed tasks")

        existing = (
            self.db.query(TaskRating)
            .filter(
                TaskRating.task_id == task_id,
                TaskRating.rater_agent_id == rater_agent_id,
                TaskRating.rated_agent_id == rated_agent_id,
                TaskRating.dimension == dimension.value,
            )
            .first()
        )
        if existing:
            raise AlreadyExistsError(f"Rating already exists for this dimension")

        rating = TaskRating(
            id=str(uuid.uuid4()),
            task_id=task_id,
            rater_agent_id=rater_agent_id,
            rated_agent_id=rated_agent_id,
            dimension=dimension.value,
            score=score,
            comment=comment,
        )
        self.db.add(rating)
        self.db.commit()
        self.db.refresh(rating)
        return rating

    def get_rating(self, rating_id: str) -> TaskRating:
        rating = self.db.query(TaskRating).filter(TaskRating.id == rating_id).first()
        if not rating:
            raise ResourceNotFoundError(f"Rating {rating_id} not found")
        return rating

    def get_ratings_for_task(self, task_id: str) -> List[TaskRating]:
        return self.db.query(TaskRating).filter(TaskRating.task_id == task_id).all()

    def get_ratings_for_agent(
        self,
        agent_id: str,
        dimension: Optional[RatingDimension] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[TaskRating], int]:
        query = self.db.query(TaskRating).filter(TaskRating.rated_agent_id == agent_id)

        if dimension:
            query = query.filter(TaskRating.dimension == dimension.value)

        total = query.count()
        offset = (page - 1) * size
        ratings = query.order_by(TaskRating.created_at.desc()).offset(offset).limit(size).all()
        return ratings, total

    def update_rating(
        self,
        rating_id: str,
        rater_agent_id: str,
        score: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> TaskRating:
        rating = self.get_rating(rating_id)

        if rating.rater_agent_id != rater_agent_id:
            raise PermissionDeniedError("Only the rater can update the rating")

        if score is not None:
            rating.score = score
        if comment is not None:
            rating.comment = comment

        rating.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(rating)
        return rating

    def delete_rating(self, rating_id: str, rater_agent_id: str) -> bool:
        rating = self.get_rating(rating_id)
        if rating.rater_agent_id != rater_agent_id:
            raise PermissionDeniedError("Only the rater can delete the rating")
        self.db.delete(rating)
        self.db.commit()
        return True

    def get_average_rating(
        self,
        agent_id: str,
        dimension: Optional[RatingDimension] = None,
    ) -> Optional[float]:
        query = self.db.query(func.avg(TaskRating.score)).filter(TaskRating.rated_agent_id == agent_id)

        if dimension:
            query = query.filter(TaskRating.dimension == dimension.value)

        result = query.scalar()
        return float(result) if result else None

    def get_agent_rating_summary(self, agent_id: str) -> dict:
        summary = {}
        for dim in RatingDimension:
            avg = self.get_average_rating(agent_id, dim)
            count = (
                self.db.query(func.count(TaskRating.id))
                .filter(TaskRating.rated_agent_id == agent_id, TaskRating.dimension == dim.value)
                .scalar()
            )
            summary[dim.value] = {"average": avg, "count": count}
        return summary
