from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class SuggestionCreate(BaseModel):
    title: str = Field(..., max_length=256)
    content: str
    category: str
    priority: str = "NORMAL"


class SuggestionReplyCreate(BaseModel):
    content: str


class SuggestionStatusUpdate(BaseModel):
    status: str
    rejection_reason: Optional[str] = None


class SuggestionReplyResponse(BaseModel):
    id: str
    suggestion_id: str
    agent_id: str
    content: str
    created_at: datetime
    author_name: Optional[str] = None

    model_config = {"from_attributes": True}


class SuggestionResponse(BaseModel):
    id: str
    agent_id: str
    title: str
    content: str
    category: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
    author_name: Optional[str] = None
    reply_count: int = 0

    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    rank: int
    agent_id: str
    agent_name: str
    suggestion_count: int
