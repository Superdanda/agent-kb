from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LearningRecordResponse(BaseModel):
    id: str
    learner_agent_id: str
    post_id: str
    learned_version_id: str
    learned_version_no: int
    status: str
    learn_note: Optional[str]
    learned_at: Optional[datetime]
    updated_at: datetime
    post_title: Optional[str] = None
    version_no: Optional[int] = None
    learner_name: Optional[str] = None

    model_config = {"from_attributes": True}
