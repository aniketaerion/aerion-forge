"""Task Management collection-validation tests."""

from typing import Any

from forge.tasks.identifiers import (
    build_task_fingerprint,
    build_task_id,
    build_task_set_fingerprint,
)
from forge.tasks.models import (
    EngineeringTask,
    TaskAcceptanceCriterion,
    TaskDependency,
    TaskDependencyType,
    TaskSet,
    TaskStatistics,
    TaskStatus,
    TaskValidationCategory,
    TaskValidationRequirement,
)
from forge.tasks.validator import (
    calculate_statistics,
    validate_task_set,
)


def _task(
    *,
    title: str,
    sequence: int,
    status: TaskStatus = TaskStatus.DRAFT,
    parent_task_id: str | None = None,
    dependencies: tuple[TaskDependency, ...] = (),
    **updates: Any,
) -> EngineeringTask:
    task_id = build_task_id(
        mission_id="mission-1",
        workstream_id="workstream-1",
        parent_task_id=parent_task_id,
        title=title,
        sequence=sequence,
    )

    values: dict[str, Any] = {
        "task_id": task_id,
        "task_fingerprint": "0" * 64,
        "mission_id": "mission-1",
        "workstream_id": "workstream-1",
        "parent_task_id": parent_task_id,
        "title": title,
        "description": f"Complete {title}.",
        "status": status,
        "dependencies": dependencies,
        "acceptance_criteria": (
            TaskAcceptanceCriterion(
                criterion_id=f"criterion-{sequence}",
                statement="Required behavior is verified.",
            ),
        ),
        "validation_requirements": (
            TaskValidationRequirement(
                requirement_id=f"validation-{sequence}",
                category=TaskValidationCategory.UNIT_TESTING,
                description="Unit tests pass.",
            ),
        ),
        "sequence": sequence,
    }
    values.update(updates)

    task = EngineeringTask(**values)

    return task.model_copy(
        update={
            "task_fingerprint": build_task_fingerprint(
                task
            )
        }
    )


def _set(
    tasks: tuple[EngineeringTask, ...],
    statistics: TaskStatistics | None = None,
) -> TaskSet:
    task_set = TaskSet(
        mission_id="mission-1",
        mission_fingerprint="a" * 64,
        task_set_fingerprint="0" * 64,
        tasks=tasks,
        statistics=(
            statistics
            if statistics is not None
            else calculate_statistics(tasks)
        ),
        source_fingerprints={
            "mission": "a" * 64,
        },
    )

    return task_set.model_copy(
        update={
            "task_set_fingerprint":
                build_task_set_fingerprint(task_set)
        }
    )


def test_valid_task_set_passes() -> None:
    first = _task(
        title="Define contract",
        sequence=1,
        status=TaskStatus.COMPLETED,
    )
    second = _task(
        title="Implement contract",
        sequence=2,
    )

    result = validate_task_set(
        _set((first, second))
    )

    assert result.valid
    assert result.messages == ()


def test_unknown_parent_is_rejected() -> None:
    task = _task(
        title="Child task",
        sequence=1,
        parent_task_id="task-00000000000000000000",
    )

    result = validate_task_set(_set((task,)))

    assert not result.valid
    assert any(
        message.field == "parent_task_id"
        for message in result.messages
    )


def test_parent_cycle_is_rejected() -> None:
    first = _task(
        title="First",
        sequence=1,
    )
    second = _task(
        title="Second",
        sequence=2,
        parent_task_id=first.task_id,
    )
    first = first.model_copy(
        update={"parent_task_id": second.task_id}
    )
    first = first.model_copy(
        update={
            "task_fingerprint":
                build_task_fingerprint(first)
        }
    )

    result = validate_task_set(
        _set((first, second))
    )

    assert not result.valid
    assert any(
        "Parent hierarchy contains a cycle"
        in message.message
        for message in result.messages
    )


def test_unknown_dependency_is_rejected() -> None:
    base = _task(
        title="Dependent",
        sequence=1,
    )
    dependency = TaskDependency(
        task_id=base.task_id,
        dependency_task_id=(
            "task-00000000000000000000"
        ),
        dependency_type=TaskDependencyType.REQUIRES,
        reason="Missing predecessor.",
    )
    task = base.model_copy(
        update={"dependencies": (dependency,)}
    )
    task = task.model_copy(
        update={
            "task_fingerprint":
                build_task_fingerprint(task)
        }
    )

    result = validate_task_set(_set((task,)))

    assert not result.valid
    assert any(
        "Dependency target does not exist"
        in message.message
        for message in result.messages
    )


def test_dependency_cycle_is_rejected() -> None:
    first = _task(title="First", sequence=1)
    second = _task(title="Second", sequence=2)

    first_dependency = TaskDependency(
        task_id=first.task_id,
        dependency_task_id=second.task_id,
        dependency_type=TaskDependencyType.REQUIRES,
        reason="Second is required.",
    )
    second_dependency = TaskDependency(
        task_id=second.task_id,
        dependency_task_id=first.task_id,
        dependency_type=TaskDependencyType.REQUIRES,
        reason="First is required.",
    )

    first = first.model_copy(
        update={"dependencies": (first_dependency,)}
    )
    second = second.model_copy(
        update={"dependencies": (second_dependency,)}
    )
    first = first.model_copy(
        update={
            "task_fingerprint":
                build_task_fingerprint(first)
        }
    )
    second = second.model_copy(
        update={
            "task_fingerprint":
                build_task_fingerprint(second)
        }
    )

    result = validate_task_set(
        _set((first, second))
    )

    assert not result.valid
    assert any(
        "dependency graph contains a cycle"
        in message.message
        for message in result.messages
    )


def test_completed_task_rejects_unresolved_dependency() -> None:
    predecessor = _task(
        title="Predecessor",
        sequence=1,
        status=TaskStatus.READY,
    )
    base = _task(
        title="Completed dependent",
        sequence=2,
        status=TaskStatus.COMPLETED,
    )
    dependency = TaskDependency(
        task_id=base.task_id,
        dependency_task_id=predecessor.task_id,
        dependency_type=TaskDependencyType.REQUIRES,
        reason="Predecessor must complete.",
    )
    dependent = base.model_copy(
        update={"dependencies": (dependency,)}
    )
    dependent = dependent.model_copy(
        update={
            "task_fingerprint":
                build_task_fingerprint(dependent)
        }
    )

    result = validate_task_set(
        _set((predecessor, dependent))
    )

    assert not result.valid
    assert any(
        "unresolved blocking dependencies"
        in message.message
        for message in result.messages
    )


def test_statistics_mismatch_is_rejected() -> None:
    task = _task(
        title="Task",
        sequence=1,
    )
    invalid = TaskStatistics(
        total_tasks=0,
        draft_tasks=0,
        ready_tasks=0,
        blocked_tasks=0,
        in_progress_tasks=0,
        review_tasks=0,
        validated_tasks=0,
        completed_tasks=0,
        cancelled_tasks=0,
        superseded_tasks=0,
        unresolved_dependency_count=0,
    )

    result = validate_task_set(
        _set((task,), statistics=invalid)
    )

    assert not result.valid
    assert any(
        message.field == "statistics"
        for message in result.messages
    )


def test_noncanonical_order_is_rejected() -> None:
    first = _task(title="First", sequence=1)
    second = _task(title="Second", sequence=2)

    result = validate_task_set(
        _set((second, first))
    )

    assert not result.valid
    assert any(
        "deterministic" in message.message
        for message in result.messages
    )


def test_tampered_fingerprint_is_rejected() -> None:
    task = _task(
        title="Task",
        sequence=1,
    ).model_copy(
        update={"task_fingerprint": "f" * 64}
    )

    result = validate_task_set(_set((task,)))

    assert not result.valid
    assert any(
        message.field == "task_fingerprint"
        for message in result.messages
    )
