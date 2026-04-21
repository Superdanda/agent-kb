import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.suggestion import Suggestion, SuggestionReply, SuggestionStatus
from app.models.agent import Agent


class SuggestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        agent_id: str,
        title: str,
        content: str,
        category: str,
        priority: str,
    ) -> Suggestion:
        suggestion = Suggestion(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            title=title,
            content=content,
            category=category,
            priority=priority,
        )
        self.db.add(suggestion)
        self.db.commit()
        self.db.refresh(suggestion)
        return suggestion

    def get_by_id(self, suggestion_id: str) -> Suggestion | None:
        return (
            self.db.query(Suggestion)
            .options(joinedload(Suggestion.agent))
            .filter(Suggestion.id == suggestion_id)
            .first()
        )

    def list_all(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Suggestion], int]:
        query = self.db.query(Suggestion).options(joinedload(Suggestion.agent))

        if status:
            query = query.filter(Suggestion.status == status)

        if category:
            query = query.filter(Suggestion.category == category)

        if agent_id:
            query = query.filter(Suggestion.agent_id == agent_id)

        total = query.count()
        items = query.order_by(Suggestion.created_at.desc()).offset(offset).limit(limit).all()

        return items, total

    def update_status(self, suggestion_id: str, status: str) -> Suggestion | None:
        suggestion = self.db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
        if not suggestion:
            return None
        suggestion.status = status
        self.db.commit()
        self.db.refresh(suggestion)
        return suggestion

    def add_reply(
        self,
        suggestion_id: str,
        agent_id: str,
        content: str,
    ) -> SuggestionReply:
        reply = SuggestionReply(
            id=str(uuid.uuid4()),
            suggestion_id=suggestion_id,
            agent_id=agent_id,
            content=content,
        )
        self.db.add(reply)
        self.db.commit()
        self.db.refresh(reply)
        return reply

    def get_replies(self, suggestion_id: str) -> List[SuggestionReply]:
        return (
            self.db.query(SuggestionReply)
            .options(joinedload(SuggestionReply.agent))
            .filter(SuggestionReply.suggestion_id == suggestion_id)
            .order_by(SuggestionReply.created_at.asc())
            .all()
        )

    def get_leaderboard(self, limit: int = 20) -> List[dict]:
        results = (
            self.db.query(
                Suggestion.agent_id,
                Agent.name.label("agent_name"),
                func.count(Suggestion.id).label("suggestion_count"),
            )
            .join(Agent, Suggestion.agent_id == Agent.id)
            .group_by(Suggestion.agent_id, Agent.name)
            .order_by(func.count(Suggestion.id).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "agent_id": row.agent_id,
                "agent_name": row.agent_name,
                "suggestion_count": row.suggestion_count,
            }
            for row in results
        ]
