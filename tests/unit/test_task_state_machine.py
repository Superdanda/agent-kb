import pytest

from app.core.exceptions import ConflictError
from app.modules.task_board.models.task import TaskStatus
from app.modules.task_board.services.task_state_machine import (
    TaskAction,
    assert_transition_allowed,
    target_status_for,
)


def test_claim_transition_from_unclaimed_to_in_progress():
    assert_transition_allowed(TaskStatus.UNCLAIMED, TaskAction.CLAIM)
    assert target_status_for(TaskAction.CLAIM) == TaskStatus.IN_PROGRESS


def test_submit_transition_requires_in_progress():
    assert_transition_allowed(TaskStatus.IN_PROGRESS, TaskAction.SUBMIT)

    with pytest.raises(ConflictError):
        assert_transition_allowed(TaskStatus.PENDING, TaskAction.SUBMIT)


def test_review_transitions_accept_submitted_and_review():
    assert_transition_allowed(TaskStatus.SUBMITTED, TaskAction.CONFIRM)
    assert_transition_allowed(TaskStatus.REVIEW, TaskAction.CONFIRM)
    assert_transition_allowed(TaskStatus.SUBMITTED, TaskAction.REJECT)
    assert target_status_for(TaskAction.CONFIRM) == TaskStatus.CONFIRMED
    assert target_status_for(TaskAction.REJECT) == TaskStatus.IN_PROGRESS
