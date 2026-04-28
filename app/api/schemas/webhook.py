from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


KbTaskWebhookEvent = Literal["task.created", "task.assigned", "task.updated", "task.completed"]
KbTaskStreamEvent = Literal["started", "chunk", "completed", "failed", "error"]


class KbTaskWebhookNotifyRequest(BaseModel):
    event: KbTaskWebhookEvent
    task_id: str
    agent_id: str | None = None  # Agent's UUID (used by Hermes to route the webhook)
    message: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KbTaskWebhookNotifyResponse(BaseModel):
    status: str
    task_id: str
    event: KbTaskWebhookEvent
    delivered: bool
    delivery_status_code: int | None = None
    delivery_error: str | None = None


class KbTaskStreamChunkRequest(BaseModel):
    type: KbTaskStreamEvent = "chunk"
    content: str | None = None
    message: str | None = None
    status_code: int | None = None
    delivery_id: str | None = None
    sequence: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
