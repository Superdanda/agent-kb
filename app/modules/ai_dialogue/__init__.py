# AI Dialogue Module
# Provides reusable AI conversation capabilities for business modules.
#
# Responsibilities:
# - Receive user input + file context
# - Call LLM (Anthropic) with streaming
# - Parse structured output for business actions
# - Return results to business modules
#
# Business modules (e.g., task_board) are responsible for
# executing business actions and persisting data.

from app.modules.ai_dialogue.service import AIDialogueService
from app.modules.ai_dialogue.schemas import (
    AIDialogueRequest,
    AITaskCreateResult,
    AITaskUpdateResult,
    AIBusinessAction,
)
