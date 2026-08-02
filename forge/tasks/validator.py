"""Collection-level validation for Task Management."""

from collections import Counter

from forge.tasks.identifiers import (
    build_task_fingerprint,
    build_task_set_fingerprint,
    validate_fingerprint,
    validate_task_id,
)
from forge.tasks.models import (
    EngineeringTask,
    TaskDependencyType,
    TaskManagementConfiguration,
    TaskSet,
    TaskStatistics,
    TaskStatus,
    TaskValidationMessage,
    TaskValidationResult,
    TaskValidationSeverity,
)

_RESOLVED_DEPENDENCY_STATUSES = {
    TaskStatus.COMPLETED,
}


def _message(
    *,
    severity: TaskValidationSeverity,
    field: str,
    message: str,
    task_id: str | None = None,
) -> TaskValidationMessage:
    return TaskValidationMessage(
        severity=severity,
        field=field,
        message=message,
        task_id=task_id,
    )


def calculate_statistics(
    tasks: tuple[EngineeringTask, ...],
) -> TaskStatistics:
    """Calculate deterministic aggregate task statistics."""

    statuses = Counter(task.status for task in tasks)
    task_by_id = {
        task.task_id: task
        for task in tasks
    }

    unresolved = 0

    for task in tasks:
        for dependency in task.dependencies:
            if not dependency.blocking:
                continue

            target = task_by_id.get(
                dependency.dependency_task_id
            )

            if (
                target is None
                or target.status
                not in _RESOLVED_DEPENDENCY_STATUSES
            ):
                unresolved += 1

    return TaskStatistics(
        total_tasks=len(tasks),
        draft_tasks=statuses[TaskStatus.DRAFT],
        ready_tasks=statuses[TaskStatus.READY],
        blocked_tasks=statuses[TaskStatus.BLOCKED],
        in_progress_tasks=statuses[
            TaskStatus.IN_PROGRESS
        ],
        review_tasks=statuses[TaskStatus.REVIEW],
        validated_tasks=statuses[
            TaskStatus.VALIDATED
        ],
        completed_tasks=statuses[
            TaskStatus.COMPLETED
        ],
        cancelled_tasks=statuses[
            TaskStatus.CANCELLED
        ],
        superseded_tasks=statuses[
            TaskStatus.SUPERSEDED
        ],
        unresolved_dependency_count=unresolved,
    )


def _find_cycle(
    graph: dict[str, set[str]],
) -> tuple[str, ...] | None:
    """Return one deterministic directed cycle, if present."""

    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> tuple[str, ...] | None:
        if node in visiting:
            start = path.index(node)
            return tuple([*path[start:], node])

        if node in visited:
            return None

        visiting.add(node)
        path.append(node)

        for target in sorted(graph.get(node, ())):
            cycle = visit(target)

            if cycle is not None:
                return cycle

        path.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in sorted(graph):
        cycle = visit(node)

        if cycle is not None:
            return cycle

    return None


def validate_task_set(
    task_set: TaskSet,
    configuration: TaskManagementConfiguration | None = None,
) -> TaskValidationResult:
    """Validate one canonical task set without mutation."""

    active = (
        configuration
        if configuration is not None
        else TaskManagementConfiguration()
    )

    messages: list[TaskValidationMessage] = []
    tasks = task_set.tasks
    task_by_id = {
        task.task_id: task
        for task in tasks
    }

    if len(tasks) > active.max_tasks_per_mission:
        messages.append(
            _message(
                severity=TaskValidationSeverity.ERROR,
                field="tasks",
                message=(
                    "Task count exceeds "
                    "max_tasks_per_mission."
                ),
            )
        )

    task_ids = [task.task_id for task in tasks]

    if len(task_ids) != len(set(task_ids)):
        messages.append(
            _message(
                severity=TaskValidationSeverity.ERROR,
                field="task_id",
                message="Duplicate task IDs are not allowed.",
            )
        )

    expected_order = tuple(
        sorted(
            tasks,
            key=lambda task: (
                task.sequence,
                task.task_id,
            ),
        )
    )

    if tasks != expected_order:
        messages.append(
            _message(
                severity=TaskValidationSeverity.ERROR,
                field="tasks",
                message=(
                    "Tasks must use deterministic "
                    "sequence/task_id ordering."
                ),
            )
        )

    parent_graph: dict[str, set[str]] = {
        task.task_id: set()
        for task in tasks
    }

    dependency_graph: dict[str, set[str]] = {
        task.task_id: set()
        for task in tasks
    }

    for task in tasks:
        if not validate_task_id(task.task_id):
            messages.append(
                _message(
                    severity=TaskValidationSeverity.ERROR,
                    field="task_id",
                    message="Task ID format is invalid.",
                    task_id=task.task_id,
                )
            )

        if (
            not validate_fingerprint(
                task.task_fingerprint
            )
            or build_task_fingerprint(task)
            != task.task_fingerprint
        ):
            messages.append(
                _message(
                    severity=TaskValidationSeverity.ERROR,
                    field="task_fingerprint",
                    message=(
                        "Task fingerprint does not match "
                        "canonical task content."
                    ),
                    task_id=task.task_id,
                )
            )

        if task.mission_id != task_set.mission_id:
            messages.append(
                _message(
                    severity=TaskValidationSeverity.ERROR,
                    field="mission_id",
                    message=(
                        "Task mission ID does not match "
                        "the task-set mission."
                    ),
                    task_id=task.task_id,
                )
            )

        if (
            len(task.dependencies)
            > active.max_dependencies_per_task
        ):
            messages.append(
                _message(
                    severity=TaskValidationSeverity.ERROR,
                    field="dependencies",
                    message=(
                        "Task dependency count exceeds "
                        "configuration."
                    ),
                    task_id=task.task_id,
                )
            )

        if (
            len(task.acceptance_criteria)
            > active.max_acceptance_criteria_per_task
        ):
            messages.append(
                _message(
                    severity=TaskValidationSeverity.ERROR,
                    field="acceptance_criteria",
                    message=(
                        "Acceptance-criteria count exceeds "
                        "configuration."
                    ),
                    task_id=task.task_id,
                )
            )

        if (
            len(task.validation_requirements)
            > active.max_validation_requirements_per_task
        ):
            messages.append(
                _message(
                    severity=TaskValidationSeverity.ERROR,
                    field="validation_requirements",
                    message=(
                        "Validation-requirement count "
                        "exceeds configuration."
                    ),
                    task_id=task.task_id,
                )
            )

        if task.parent_task_id is not None:
            if task.parent_task_id == task.task_id:
                messages.append(
                    _message(
                        severity=TaskValidationSeverity.ERROR,
                        field="parent_task_id",
                        message=(
                            "A task cannot be its own parent."
                        ),
                        task_id=task.task_id,
                    )
                )
            elif task.parent_task_id not in task_by_id:
                messages.append(
                    _message(
                        severity=TaskValidationSeverity.ERROR,
                        field="parent_task_id",
                        message=(
                            "Parent task does not exist."
                        ),
                        task_id=task.task_id,
                    )
                )
            else:
                parent_graph[task.task_id].add(
                    task.parent_task_id
                )

        for dependency in task.dependencies:
            if dependency.task_id != task.task_id:
                messages.append(
                    _message(
                        severity=TaskValidationSeverity.ERROR,
                        field="dependencies",
                        message=(
                            "Dependency source task does not "
                            "match its containing task."
                        ),
                        task_id=task.task_id,
                    )
                )

            if (
                dependency.dependency_task_id
                not in task_by_id
            ):
                messages.append(
                    _message(
                        severity=TaskValidationSeverity.ERROR,
                        field="dependencies",
                        message=(
                            "Dependency target does not exist."
                        ),
                        task_id=task.task_id,
                    )
                )
                continue

            if dependency.dependency_type in {
                TaskDependencyType.REQUIRES,
                TaskDependencyType.BLOCKS,
            }:
                dependency_graph[task.task_id].add(
                    dependency.dependency_task_id
                )

        if (
            task.status is TaskStatus.COMPLETED
            and any(
                dependency.blocking
                and (
                    task_by_id.get(
                        dependency.dependency_task_id
                    ) is None
                    or task_by_id[
                        dependency.dependency_task_id
                    ].status
                    not in _RESOLVED_DEPENDENCY_STATUSES
                )
                for dependency in task.dependencies
            )
        ):
            messages.append(
                _message(
                    severity=TaskValidationSeverity.ERROR,
                    field="status",
                    message=(
                        "Completed task has unresolved "
                        "blocking dependencies."
                    ),
                    task_id=task.task_id,
                )
            )

    parent_cycle = _find_cycle(parent_graph)

    if parent_cycle is not None:
        messages.append(
            _message(
                severity=TaskValidationSeverity.ERROR,
                field="parent_task_id",
                message=(
                    "Parent hierarchy contains a cycle: "
                    + " -> ".join(parent_cycle)
                ),
            )
        )

    dependency_cycle = _find_cycle(
        dependency_graph
    )

    if dependency_cycle is not None:
        messages.append(
            _message(
                severity=TaskValidationSeverity.ERROR,
                field="dependencies",
                message=(
                    "Task dependency graph contains a cycle: "
                    + " -> ".join(dependency_cycle)
                ),
            )
        )

    expected_statistics = calculate_statistics(tasks)

    if task_set.statistics != expected_statistics:
        messages.append(
            _message(
                severity=TaskValidationSeverity.ERROR,
                field="statistics",
                message=(
                    "Task statistics do not match "
                    "canonical task content."
                ),
            )
        )

    if (
        not validate_fingerprint(
            task_set.task_set_fingerprint
        )
        or build_task_set_fingerprint(task_set)
        != task_set.task_set_fingerprint
    ):
        messages.append(
            _message(
                severity=TaskValidationSeverity.ERROR,
                field="task_set_fingerprint",
                message=(
                    "Task-set fingerprint does not match "
                    "canonical content."
                ),
            )
        )

    ordered = tuple(
        sorted(
            messages,
            key=lambda message: (
                message.severity.value,
                message.field,
                message.task_id or "",
                message.message,
            ),
        )
    )

    return TaskValidationResult(
        valid=not any(
            message.severity
            is TaskValidationSeverity.ERROR
            for message in ordered
        ),
        messages=ordered,
    )
