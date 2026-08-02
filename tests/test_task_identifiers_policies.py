"""Task identifier and lifecycle-policy tests."""

import pytest

from forge.tasks.errors import (
    TaskIdentifierError,
    TaskLifecycleError,
)
from forge.tasks.identifiers import (
    build_task_fingerprint,
    build_task_id,
    normalize_task_title,
    validate_fingerprint,
    validate_task_id,
)
from forge.tasks.models import (
    EngineeringTask,
    TaskAcceptanceCriterion,
    TaskRiskLevel,
    TaskStatus,
    TaskValidationCategory,
    TaskValidationRequirement,
)
from forge.tasks.policies import (
    MILESTONE_EXCLUSIONS,
    can_transition,
    highest_risk,
    is_terminal,
    validate_transition,
)


def _task(task_id: str) -> EngineeringTask:
    task = EngineeringTask(
        task_id=task_id,
        task_fingerprint="0" * 64,
        mission_id="mission-1",
        workstream_id="workstream-1",
        title="Implement Procurement Validation",
        description="Implement the approved validation contract.",
        acceptance_criteria=(
            TaskAcceptanceCriterion(
                criterion_id="criterion-1",
                statement="The behavior is verified.",
            ),
        ),
        validation_requirements=(
            TaskValidationRequirement(
                requirement_id="validation-1",
                category=TaskValidationCategory.UNIT_TESTING,
                description="Unit tests pass.",
            ),
        ),
        sequence=1,
    )

    fingerprint = build_task_fingerprint(task)

    return task.model_copy(
        update={"task_fingerprint": fingerprint}
    )


def test_task_id_is_deterministic() -> None:
    first = build_task_id(
        mission_id="mission-1",
        workstream_id="workstream-1",
        parent_task_id=None,
        title="  Implement   Procurement Validation ",
        sequence=1,
    )
    second = build_task_id(
        mission_id="mission-1",
        workstream_id="workstream-1",
        parent_task_id=None,
        title="implement procurement validation",
        sequence=1,
    )

    assert first == second
    assert validate_task_id(first)


def test_identity_changes_for_stable_identity_fields() -> None:
    base = build_task_id(
        mission_id="mission-1",
        workstream_id="workstream-1",
        parent_task_id=None,
        title="Implement Procurement Validation",
        sequence=1,
    )
    changed = build_task_id(
        mission_id="mission-1",
        workstream_id="workstream-1",
        parent_task_id=None,
        title="Implement Procurement Validation",
        sequence=2,
    )

    assert base != changed


def test_invalid_identity_inputs_are_rejected() -> None:
    with pytest.raises(TaskIdentifierError):
        normalize_task_title(" ")

    with pytest.raises(TaskIdentifierError):
        build_task_id(
            mission_id="",
            workstream_id="workstream-1",
            parent_task_id=None,
            title="Task",
            sequence=1,
        )

    with pytest.raises(TaskIdentifierError):
        build_task_id(
            mission_id="mission-1",
            workstream_id="workstream-1",
            parent_task_id=None,
            title="Task",
            sequence=-1,
        )


def test_task_fingerprint_is_deterministic() -> None:
    task_id = build_task_id(
        mission_id="mission-1",
        workstream_id="workstream-1",
        parent_task_id=None,
        title="Implement Procurement Validation",
        sequence=1,
    )
    task = _task(task_id)

    assert build_task_fingerprint(task) == task.task_fingerprint
    assert validate_fingerprint(task.task_fingerprint)


def test_lifecycle_policy_allows_valid_transitions() -> None:
    assert can_transition(
        TaskStatus.DRAFT,
        TaskStatus.READY,
    )
    assert can_transition(
        TaskStatus.READY,
        TaskStatus.IN_PROGRESS,
    )
    assert can_transition(
        TaskStatus.REVIEW,
        TaskStatus.VALIDATED,
    )
    assert can_transition(
        TaskStatus.VALIDATED,
        TaskStatus.COMPLETED,
    )


def test_terminal_states_reject_transitions() -> None:
    assert is_terminal(TaskStatus.COMPLETED)
    assert is_terminal(TaskStatus.CANCELLED)
    assert is_terminal(TaskStatus.SUPERSEDED)

    with pytest.raises(TaskLifecycleError):
        validate_transition(
            TaskStatus.COMPLETED,
            TaskStatus.READY,
        )


def test_highest_risk_uses_controlled_order() -> None:
    assert highest_risk(
        (
            TaskRiskLevel.LOW,
            TaskRiskLevel.CRITICAL,
            TaskRiskLevel.MEDIUM,
        )
    ) is TaskRiskLevel.CRITICAL

    assert highest_risk(()) is TaskRiskLevel.UNKNOWN


def test_milestone_exclusions_preserve_non_execution_boundary() -> None:
    assert "source-code editing" in MILESTONE_EXCLUSIONS
    assert "autonomous task execution" in MILESTONE_EXCLUSIONS
    assert "git mutation" in MILESTONE_EXCLUSIONS
