"""Task query API tests."""

from forge.tasks.identifiers import (
    build_task_fingerprint,
    build_task_id,
)
from forge.tasks.models import (
    EngineeringTask,
    TaskAcceptanceCriterion,
    TaskDependency,
    TaskDependencyType,
    TaskGeneration,
    TaskPriority,
    TaskRiskLevel,
    TaskStatistics,
    TaskStatus,
    TaskStore,
    TaskValidationCategory,
    TaskValidationRequirement,
)
from forge.tasks.query import TaskQuery


def _task(
    *,
    title: str,
    sequence: int,
    status: TaskStatus = TaskStatus.DRAFT,
    priority: TaskPriority = TaskPriority.MEDIUM,
    risk: TaskRiskLevel = TaskRiskLevel.MEDIUM,
    parent_task_id: str | None = None,
    dependencies: tuple[TaskDependency, ...] = (),
    workstream_id: str = "workstream-1",
) -> EngineeringTask:
    task_id = build_task_id(
        mission_id="mission-1",
        workstream_id=workstream_id,
        parent_task_id=parent_task_id,
        title=title,
        sequence=sequence,
    )

    task = EngineeringTask(
        task_id=task_id,
        task_fingerprint="0" * 64,
        mission_id="mission-1",
        workstream_id=workstream_id,
        parent_task_id=parent_task_id,
        title=title,
        description=f"Complete {title}.",
        status=status,
        priority=priority,
        risk_level=risk,
        dependencies=dependencies,
        acceptance_criteria=(
            TaskAcceptanceCriterion(
                criterion_id=f"criterion-{sequence}",
                statement="Required behavior is verified.",
            ),
        ),
        validation_requirements=(
            TaskValidationRequirement(
                requirement_id=f"validation-{sequence}",
                category=TaskValidationCategory.UNIT_TESTING,
                description="Unit tests pass.",
            ),
        ),
        sequence=sequence,
        blocking_reason=(
            "Waiting for predecessor."
            if status is TaskStatus.BLOCKED
            else None
        ),
    )

    return task.model_copy(
        update={
            "task_fingerprint": build_task_fingerprint(task),
        }
    )


def _store() -> tuple[TaskStore, dict[str, EngineeringTask]]:
    parent = _task(
        title="Parent",
        sequence=1,
        status=TaskStatus.READY,
        priority=TaskPriority.HIGH,
        risk=TaskRiskLevel.HIGH,
    )
    child = _task(
        title="Child",
        sequence=2,
        parent_task_id=parent.task_id,
    )
    predecessor = _task(
        title="Predecessor",
        sequence=3,
        status=TaskStatus.COMPLETED,
        workstream_id="workstream-2",
    )

    dependency = TaskDependency(
        task_id=child.task_id,
        dependency_task_id=predecessor.task_id,
        dependency_type=TaskDependencyType.REQUIRES,
        reason="Predecessor is required.",
    )
    child = child.model_copy(
        update={
            "dependencies": (dependency,),
            "task_fingerprint": "0" * 64,
        }
    )
    child = child.model_copy(
        update={
            "task_fingerprint": build_task_fingerprint(child),
        }
    )

    tasks = {
        task.task_id: task
        for task in (child, predecessor, parent)
    }

    statistics = TaskStatistics(
        total_tasks=3,
        draft_tasks=1,
        ready_tasks=1,
        blocked_tasks=0,
        in_progress_tasks=0,
        review_tasks=0,
        validated_tasks=0,
        completed_tasks=1,
        cancelled_tasks=0,
        superseded_tasks=0,
        unresolved_dependency_count=0,
    )

    generation = TaskGeneration(
        generation_id="task-generation-1",
        mission_id="mission-1",
        mission_fingerprint="a" * 64,
        task_set_fingerprint="b" * 64,
        task_count=3,
        statistics=statistics,
    )

    return (
        TaskStore(
            tasks=tasks,
            generations={"mission-1": generation},
        ),
        {
            "parent": parent,
            "child": child,
            "predecessor": predecessor,
        },
    )


def test_list_tasks_is_deterministic() -> None:
    store, tasks = _store()
    query = TaskQuery(store)

    assert query.list_tasks() == (
        tasks["parent"],
        tasks["child"],
        tasks["predecessor"],
    )


def test_filters_by_mission_workstream_status_priority_and_risk() -> None:
    store, tasks = _store()
    query = TaskQuery(store)

    assert len(query.list_tasks_for_mission("mission-1")) == 3
    assert query.list_tasks_for_workstream("workstream-2") == (
        tasks["predecessor"],
    )
    assert query.list_ready_tasks() == (tasks["parent"],)
    assert query.list_tasks_by_priority(TaskPriority.HIGH) == (
        tasks["parent"],
    )
    assert query.list_tasks_by_risk(TaskRiskLevel.HIGH) == (
        tasks["parent"],
    )


def test_parent_and_children_queries() -> None:
    store, tasks = _store()
    query = TaskQuery(store)

    assert query.get_parent(tasks["child"].task_id) == tasks["parent"]
    assert query.get_parent(tasks["parent"].task_id) is None
    assert query.get_children(tasks["parent"].task_id) == (
        tasks["child"],
    )


def test_dependency_queries() -> None:
    store, tasks = _store()
    query = TaskQuery(store)

    assert query.get_dependencies(tasks["child"].task_id) == (
        tasks["predecessor"],
    )
    assert query.get_dependents(tasks["predecessor"].task_id) == (
        tasks["child"],
    )


def test_generation_statistics_and_completion() -> None:
    store, _ = _store()
    query = TaskQuery(store)

    assert query.get_generation("mission-1").task_count == 3
    assert query.get_statistics("mission-1").total_tasks == 3
    assert not query.is_complete("mission-1")


def test_query_uses_deep_copy() -> None:
    store, tasks = _store()
    query = TaskQuery(store)

    store.tasks.clear()

    assert query.get_task(tasks["parent"].task_id) == tasks["parent"]
