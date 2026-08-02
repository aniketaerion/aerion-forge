"""Task Management foundation-model tests."""

from typing import Any

import pytest
from pydantic import ValidationError

from forge.tasks.models import (
    SCHEMA_VERSION,
    EngineeringTask,
    TaskAcceptanceCriterion,
    TaskDependency,
    TaskDependencyType,
    TaskManagementConfiguration,
    TaskOwner,
    TaskOwnershipType,
    TaskPriority,
    TaskRiskLevel,
    TaskStatus,
    TaskStore,
    TaskValidationCategory,
    TaskValidationRequirement,
)


def _criterion() -> TaskAcceptanceCriterion:
    return TaskAcceptanceCriterion(
        criterion_id="criterion-1",
        statement="The required behavior is verified.",
    )


def _validation() -> TaskValidationRequirement:
    return TaskValidationRequirement(
        requirement_id="validation-1",
        category=TaskValidationCategory.UNIT_TESTING,
        description="Unit tests pass.",
    )


def _task(**updates: Any) -> EngineeringTask:
    values: dict[str, Any] = {
        "task_id": "task-00000000000000000001",
        "task_fingerprint": "a" * 64,
        "mission_id": "mission-1",
        "workstream_id": "workstream-1",
        "title": "Implement procurement validation",
        "description": "Implement the approved validation contract.",
        "status": TaskStatus.DRAFT,
        "priority": TaskPriority.MEDIUM,
        "risk_level": TaskRiskLevel.MEDIUM,
        "acceptance_criteria": (_criterion(),),
        "validation_requirements": (_validation(),),
        "sequence": 1,
    }
    values.update(updates)
    return EngineeringTask(**values)


def test_schema_and_configuration_defaults() -> None:
    configuration = TaskManagementConfiguration()

    assert SCHEMA_VERSION == "1.0"
    assert configuration.enabled
    assert not configuration.strict
    assert configuration.history_limit == 5
    assert configuration.max_tasks_per_mission == 250


def test_task_is_frozen_and_forbids_extra_fields() -> None:
    task = _task()

    with pytest.raises(ValidationError):
        task.title = "Changed"

    invalid_payload = task.model_dump()
    invalid_payload["unexpected"] = True

    with pytest.raises(ValidationError):
        EngineeringTask.model_validate(invalid_payload)


def test_unassigned_owner_rejects_owner_details() -> None:
    with pytest.raises(ValidationError):
        TaskOwner(
            ownership_type=TaskOwnershipType.UNASSIGNED,
            owner_id="person-1",
            display_name="Person One",
        )


def test_assigned_owner_requires_complete_details() -> None:
    with pytest.raises(ValidationError):
        TaskOwner(
            ownership_type=TaskOwnershipType.PERSON,
            owner_id="person-1",
        )


def test_self_dependency_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskDependency(
            task_id="task-1",
            dependency_task_id="task-1",
            dependency_type=TaskDependencyType.REQUIRES,
            reason="Invalid self-dependency.",
        )


def test_blocked_task_requires_reason() -> None:
    with pytest.raises(ValidationError):
        _task(
            status=TaskStatus.BLOCKED,
            blocking_reason=None,
        )


def test_non_blocked_task_rejects_blocking_reason() -> None:
    with pytest.raises(ValidationError):
        _task(
            status=TaskStatus.READY,
            blocking_reason="Incorrect state.",
        )


def test_task_requires_acceptance_and_validation_contracts() -> None:
    with pytest.raises(ValidationError):
        _task(acceptance_criteria=())

    with pytest.raises(ValidationError):
        _task(validation_requirements=())


def test_duplicate_dependency_targets_are_rejected() -> None:
    dependency = TaskDependency(
        task_id="task-00000000000000000001",
        dependency_task_id="task-2",
        dependency_type=TaskDependencyType.REQUIRES,
        reason="Required predecessor.",
    )

    with pytest.raises(ValidationError):
        _task(dependencies=(dependency, dependency))


def test_store_defaults_are_safe() -> None:
    store = TaskStore()

    assert store.schema_version == "1.0"
    assert store.tasks == {}
    assert store.history == {}
    assert store.generations == {}
