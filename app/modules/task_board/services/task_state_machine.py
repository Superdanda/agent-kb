"""Task board state machine helpers.

All Agent task routes should validate transitions through this module so the
legacy `/api/agent/tasks/*` routes and the canonical `/api/tasks/*` routes stay
consistent.
"""

from enum import Enum

from app.core.exceptions import ConflictError
from app.modules.task_board.models.task import TaskStatus


class TaskAction(str, Enum):
    CLAIM = "claim"
    SUBMIT = "submit"
    ABANDON = "abandon"
    CONFIRM = "confirm"
    REJECT = "reject"


ALLOWED_TRANSITIONS: dict[TaskAction, set[TaskStatus]] = {
    TaskAction.CLAIM: {TaskStatus.PENDING, TaskStatus.UNCLAIMED},
    TaskAction.SUBMIT: {TaskStatus.IN_PROGRESS},
    TaskAction.ABANDON: {TaskStatus.IN_PROGRESS},
    TaskAction.CONFIRM: {TaskStatus.SUBMITTED, TaskStatus.REVIEW},
    TaskAction.REJECT: {TaskStatus.SUBMITTED, TaskStatus.REVIEW},
}

TARGET_STATUS: dict[TaskAction, TaskStatus] = {
    TaskAction.CLAIM: TaskStatus.IN_PROGRESS,
    TaskAction.SUBMIT: TaskStatus.SUBMITTED,
    TaskAction.ABANDON: TaskStatus.UNCLAIMED,
    TaskAction.CONFIRM: TaskStatus.CONFIRMED,
    TaskAction.REJECT: TaskStatus.IN_PROGRESS,
}


def assert_transition_allowed(current_status: TaskStatus, action: TaskAction) -> None:
    allowed = ALLOWED_TRANSITIONS[action]
    if current_status not in allowed:
        allowed_values = ", ".join(sorted(status.value for status in allowed))
        raise ConflictError(
            f"Task action '{action.value}' is not allowed from status "
            f"'{current_status.value}'. Allowed source statuses: {allowed_values}"
        )


def target_status_for(action: TaskAction) -> TaskStatus:
    return TARGET_STATUS[action]
