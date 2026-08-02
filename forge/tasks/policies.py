"""Lifecycle and safety policies for Task Management."""

from forge.tasks.errors import TaskLifecycleError
from forge.tasks.models import (
    TaskRiskLevel,
    TaskStatus,
)

POLICY_VERSION = "1.0"

TERMINAL_STATUSES = frozenset(
    {
        TaskStatus.COMPLETED,
        TaskStatus.CANCELLED,
        TaskStatus.SUPERSEDED,
    }
)

ACTIVE_STATUSES = frozenset(
    {
        TaskStatus.DRAFT,
        TaskStatus.READY,
        TaskStatus.BLOCKED,
        TaskStatus.IN_PROGRESS,
        TaskStatus.REVIEW,
        TaskStatus.VALIDATED,
    }
)

ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.DRAFT: frozenset(
        {
            TaskStatus.READY,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.READY: frozenset(
        {
            TaskStatus.IN_PROGRESS,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.BLOCKED: frozenset(
        {
            TaskStatus.READY,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.IN_PROGRESS: frozenset(
        {
            TaskStatus.REVIEW,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.REVIEW: frozenset(
        {
            TaskStatus.IN_PROGRESS,
            TaskStatus.VALIDATED,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.VALIDATED: frozenset(
        {
            TaskStatus.COMPLETED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.SUPERSEDED,
        }
    ),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
    TaskStatus.SUPERSEDED: frozenset(),
}

RISK_ORDER: dict[TaskRiskLevel, int] = {
    TaskRiskLevel.UNKNOWN: 0,
    TaskRiskLevel.LOW: 1,
    TaskRiskLevel.MEDIUM: 2,
    TaskRiskLevel.HIGH: 3,
    TaskRiskLevel.CRITICAL: 4,
}

MILESTONE_EXCLUSIONS = (
    "source-code editing",
    "patch generation",
    "target build execution",
    "target test execution",
    "database migration execution",
    "shell execution",
    "git mutation",
    "deployment",
    "automatic remediation",
    "autonomous task execution",
)


def can_transition(
    current: TaskStatus,
    target: TaskStatus,
) -> bool:
    """Return whether a lifecycle transition is permitted."""

    if current is target:
        return True

    return target in ALLOWED_TRANSITIONS[current]


def validate_transition(
    current: TaskStatus,
    target: TaskStatus,
) -> None:
    """Raise when a lifecycle transition violates policy."""

    if not can_transition(current, target):
        raise TaskLifecycleError(
            f"Task transition is not allowed: "
            f"{current.value} -> {target.value}"
        )


def is_terminal(status: TaskStatus) -> bool:
    """Return whether a task status is terminal."""

    return status in TERMINAL_STATUSES


def highest_risk(
    risks: tuple[TaskRiskLevel, ...],
) -> TaskRiskLevel:
    """Return the highest task risk using controlled ordering."""

    if not risks:
        return TaskRiskLevel.UNKNOWN

    return max(
        risks,
        key=lambda risk: RISK_ORDER[risk],
    )
