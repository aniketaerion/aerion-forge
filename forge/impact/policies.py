"""Policies for Milestone 2.3 Impact Decision."""

from forge.impact.errors import ImpactValidationError
from forge.impact.models import (
    DecisionStatus,
    ImpactSeverity,
)

MILESTONE_EXCLUSIONS = (
    "task execution",
    "source-code modification",
    "build execution",
    "test execution",
    "database migration execution",
    "git mutation",
    "deployment",
    "approval granting",
    "autonomous remediation",
)

TERMINAL_STATUSES = {
    DecisionStatus.SUPERSEDED,
}

_ALLOWED_TRANSITIONS: dict[
    DecisionStatus,
    frozenset[DecisionStatus],
] = {
    DecisionStatus.DRAFT: frozenset(
        {
            DecisionStatus.READY,
            DecisionStatus.READY_WITH_CONDITIONS,
            DecisionStatus.BLOCKED,
            DecisionStatus.APPROVAL_REQUIRED,
            DecisionStatus.SUPERSEDED,
        }
    ),
    DecisionStatus.READY: frozenset(
        {
            DecisionStatus.READY_WITH_CONDITIONS,
            DecisionStatus.BLOCKED,
            DecisionStatus.APPROVAL_REQUIRED,
            DecisionStatus.SUPERSEDED,
        }
    ),
    DecisionStatus.READY_WITH_CONDITIONS: frozenset(
        {
            DecisionStatus.READY,
            DecisionStatus.BLOCKED,
            DecisionStatus.APPROVAL_REQUIRED,
            DecisionStatus.SUPERSEDED,
        }
    ),
    DecisionStatus.BLOCKED: frozenset(
        {
            DecisionStatus.DRAFT,
            DecisionStatus.READY,
            DecisionStatus.READY_WITH_CONDITIONS,
            DecisionStatus.APPROVAL_REQUIRED,
            DecisionStatus.SUPERSEDED,
        }
    ),
    DecisionStatus.APPROVAL_REQUIRED: frozenset(
        {
            DecisionStatus.READY,
            DecisionStatus.READY_WITH_CONDITIONS,
            DecisionStatus.BLOCKED,
            DecisionStatus.SUPERSEDED,
        }
    ),
    DecisionStatus.SUPERSEDED: frozenset(),
}

_SEVERITY_ORDER = {
    ImpactSeverity.NONE: 0,
    ImpactSeverity.UNKNOWN: 1,
    ImpactSeverity.LOW: 2,
    ImpactSeverity.MEDIUM: 3,
    ImpactSeverity.HIGH: 4,
    ImpactSeverity.CRITICAL: 5,
}


def can_transition(
    current: DecisionStatus,
    target: DecisionStatus,
) -> bool:
    """Return whether a decision-state transition is permitted."""

    if current is target:
        return True

    return target in _ALLOWED_TRANSITIONS[current]


def validate_transition(
    current: DecisionStatus,
    target: DecisionStatus,
) -> None:
    """Raise when a lifecycle transition violates policy."""

    if not can_transition(current, target):
        raise ImpactValidationError(
            f"Impact decision transition is not allowed: {current.value} -> {target.value}."
        )


def is_terminal(status: DecisionStatus) -> bool:
    """Return whether a decision status is terminal."""

    return status in TERMINAL_STATUSES


def highest_severity(
    severities: tuple[ImpactSeverity, ...],
) -> ImpactSeverity:
    """Return the highest controlled impact severity."""

    if not severities:
        return ImpactSeverity.UNKNOWN

    return max(
        severities,
        key=lambda severity: _SEVERITY_ORDER[severity],
    )
