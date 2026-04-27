from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class AIDialogueRequest(BaseModel):
    """Request to the AI dialogue module."""
    business_scenario: str  # "task_create" or "task_edit"
    user_message: str
    file_context: Optional[List[Dict[str, Any]]] = None  # [{filename, content_type, size}]
    current_task: Optional[Dict[str, Any]] = None  # For edit scenario: current task fields
    available_agents: Optional[List[Dict[str, str]]] = None  # [{id, name, agent_code}]
    conversation_history: Optional[List[Dict[str, str]]] = None  # [{role, content}]


class FieldChange(BaseModel):
    """Description of a single field change."""
    field: str
    label: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class AIBusinessAction(BaseModel):
    """Structured result returned from AI for business execution."""
    action: str  # "create_task" or "update_task"
    task_id: Optional[str] = None  # Set for update actions
    fields: Dict[str, Any] = {}
    changes: Optional[List[FieldChange]] = None  # For edit: what changed
    summary: str = ""  # Human-readable summary of what was done


class AITaskCreateResult(BaseModel):
    """Result of AI task creation."""
    task_id: str
    title: str
    fields: Dict[str, Any]
    summary: str


class AITaskUpdateResult(BaseModel):
    """Result of AI task update."""
    task_id: str
    title: str
    changes: List[FieldChange]
    summary: str


class SSEEvent(BaseModel):
    """An SSE event to be sent to the frontend."""
    event: str  # "thinking", "text", "task_created", "task_updated", "error", "done"
    data: str
