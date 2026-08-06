"""State transitions for autonomous mission orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from forge.autonomous_orchestration.errors import (
    OrchestrationStateError,
)
from forge.autonomous_orchestration.states import (
    TERMINAL_ORCHESTRATION_STATES,
    OrchestrationState,
)

_TRANSITIONS: dict[
    OrchestrationState,
    frozenset[OrchestrationState],
] = {
    OrchestrationState.CREATED: frozenset(
        {
            OrchestrationState.INITIALIZING,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.INITIALIZING: frozenset(
        {
            OrchestrationState.PLAN_LOADING,
            OrchestrationState.FAILED,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.PLAN_LOADING: frozenset(
        {
            OrchestrationState.READY,
            OrchestrationState.AWAITING_APPROVAL,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.READY: frozenset(
        {
            OrchestrationState.STEP_SELECTING,
            OrchestrationState.PAUSED,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.STEP_SELECTING: frozenset(
        {
            OrchestrationState.STEP_PREPARING,
            OrchestrationState.AWAITING_APPROVAL,
            OrchestrationState.COMPLETED,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.STEP_PREPARING: frozenset(
        {
            OrchestrationState.STEP_EXECUTING,
            OrchestrationState.AWAITING_APPROVAL,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.STEP_EXECUTING: frozenset(
        {
            OrchestrationState.OUTCOME_PROCESSING,
            OrchestrationState.RETRY_PENDING,
            OrchestrationState.ROLLBACK_PENDING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.OUTCOME_PROCESSING: frozenset(
        {
            OrchestrationState.PROGRESS_UPDATING,
            OrchestrationState.RETRY_PENDING,
            OrchestrationState.ROLLBACK_PENDING,
            OrchestrationState.REPLAN_PENDING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.PROGRESS_UPDATING: frozenset(
        {
            OrchestrationState.CONTINUE_CHECK,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.CONTINUE_CHECK: frozenset(
        {
            OrchestrationState.STEP_SELECTING,
            OrchestrationState.AWAITING_APPROVAL,
            OrchestrationState.RETRY_PENDING,
            OrchestrationState.ROLLBACK_PENDING,
            OrchestrationState.REPLAN_PENDING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.COMPLETED,
            OrchestrationState.FAILED,
            OrchestrationState.CANCELLED,
        }
    ),
    OrchestrationState.AWAITING_APPROVAL: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.PAUSED,
            OrchestrationState.CANCELLED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.RETRY_PENDING: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.ROLLBACK_PENDING: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.REPLAN_PENDING: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.PAUSED: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.CANCELLED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.RESUME_VALIDATING: frozenset(
        {
            OrchestrationState.READY,
            OrchestrationState.AWAITING_APPROVAL,
            OrchestrationState.PAUSED,
            OrchestrationState.ESCALATED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.ESCALATED: frozenset(
        {
            OrchestrationState.RESUME_VALIDATING,
            OrchestrationState.PAUSED,
            OrchestrationState.CANCELLED,
            OrchestrationState.FAILED,
        }
    ),
    OrchestrationState.COMPLETED: frozenset(),
    OrchestrationState.FAILED: frozenset(),
    OrchestrationState.CANCELLED: frozenset(),
}

ORCHESTRATION_TRANSITIONS: Final[
    Mapping[
        OrchestrationState,
        frozenset[OrchestrationState],
    ]
] = MappingProxyType(_TRANSITIONS)


def assert_orchestration_transition(
    current: OrchestrationState,
    target: OrchestrationState,
) -> None:
    """Raise when an orchestration transition is illegal."""
    if current in TERMINAL_ORCHESTRATION_STATES:
        raise OrchestrationStateError(
            f"Terminal orchestration cannot transition "
            f"from {current.value}."
        )

    if target not in ORCHESTRATION_TRANSITIONS[current]:
        raise OrchestrationStateError(
            f"Illegal orchestration transition: "
            f"{current.value} -> {target.value}"
        )