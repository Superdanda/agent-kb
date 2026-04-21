import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from app.repositories.suggestion_repo import SuggestionRepository
from app.models.suggestion import SuggestionStatus
from app.core.exceptions import ResourceNotFoundError


def _suggestion_to_dict(s: "Suggestion", replies: list = None) -> dict:
    return {
        "id": s.id,
        "agent_id": s.agent_id,
        "title": s.title,
        "content": s.content,
        "category": s.category,
        "status": s.status,
        "priority": s.priority,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "author_name": s.agent.name if s.agent else s.agent_id,
        "reply_count": len(replies) if replies is not None else 0,
        "replies": replies,
    }


def _reply_to_dict(r: "SuggestionReply") -> dict:
    return {
        "id": r.id,
        "suggestion_id": r.suggestion_id,
        "agent_id": r.agent_id,
        "content": r.content,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "author_name": r.agent.name if r.agent else r.agent_id,
    }


class SuggestionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SuggestionRepository(db)

    def submit_suggestion(self, agent_id: str, title: str, content: str,
                          category: str, priority: str = "NORMAL") -> dict:
        suggestion = self.repo.create(
            agent_id=agent_id,
            title=title,
            content=content,
            category=category,
            priority=priority,
        )
        return _suggestion_to_dict(suggestion, replies=[])

    def list_suggestions(self, status: Optional[str] = None,
                         category: Optional[str] = None,
                         agent_id: Optional[str] = None,
                         limit: int = 50, offset: int = 0) -> dict:
        items, total = self.repo.list_all(
            status=status, category=category, agent_id=agent_id,
            limit=limit, offset=offset,
        )
        return {
            "items": [_suggestion_to_dict(s) for s in items],
            "total": total,
        }

    def get_suggestion(self, suggestion_id: str) -> dict:
        suggestion = self.repo.get_by_id(suggestion_id)
        if not suggestion:
            raise ResourceNotFoundError(f"Suggestion {suggestion_id} not found")
        replies = list(suggestion.replies)
        return _suggestion_to_dict(suggestion, replies=[_reply_to_dict(r) for r in replies])

    def resolve_suggestion(self, suggestion_id: str,
                           resolver_agent_id: str,
                           rejection_reason: Optional[str] = None) -> dict:
        suggestion = self.repo.get_by_id(suggestion_id)
        if not suggestion:
            raise ResourceNotFoundError(f"Suggestion {suggestion_id} not found")
        new_status = SuggestionStatus.REJECTED.value if rejection_reason else SuggestionStatus.RESOLVED.value
        suggestion = self.repo.update_status(suggestion_id, new_status)
        # add a reply recording the resolution
        content = f"Rejected: {rejection_reason}" if rejection_reason else "Resolved."
        self.repo.add_reply(suggestion_id, resolver_agent_id, content)
        replies = list(suggestion.replies)
        return _suggestion_to_dict(suggestion, replies=[_reply_to_dict(r) for r in replies])

    def add_reply(self, suggestion_id: str, agent_id: str, content: str) -> dict:
        suggestion = self.repo.get_by_id(suggestion_id)
        if not suggestion:
            raise ResourceNotFoundError(f"Suggestion {suggestion_id} not found")
        reply = self.repo.add_reply(suggestion_id, agent_id, content)
        return _reply_to_dict(reply)

    def get_leaderboard(self, limit: int = 20) -> List[dict]:
        rows = self.repo.get_leaderboard(limit=limit)
        return [
            {
                "rank": idx + 1,
                "agent_id": row["agent_id"],
                "agent_name": row["agent_name"],
                "suggestion_count": row["suggestion_count"],
            }
            for idx, row in enumerate(rows)
        ]
