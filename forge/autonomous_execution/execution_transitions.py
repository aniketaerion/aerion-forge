"""State transitions for one autonomous step execution."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_execution.states import (
    TERMINAL_EXECUTION_STATES,
    StepExecutionState,
)

_TRANSITIONS: dict[
    StepExecutionState,
    frozenset[StepExecutionState],
] = {
    StepExecutionState.PENDING: frozenset(
        {
            StepExecutionState.ELIGIBILITY_CHECK,
            StepExecutionState.CANCELLED,
        }
    ),
    StepExecutionState.ELIGIBILITY_CHECK: frozenset(
        {
            StepExecutionState.READY,
            StepExecutionState.BLOCKED,
            StepExecutionState.AWAITING_APPROVAL,
            StepExecutionState.FAILED,
            StepExecutionState.CANCELLED,
        }
    ),
    StepExecutionState.READY: frozenset(
        {
            StepExecutionState.LEASE_ACQUIRING,
            StepExecutionState.PAUSED,
            StepExecutionState.CANCELLED,
        }
    ),
    StepExecutionState.LEASE_ACQUIRING: frozenset(
        {
            StepExecutionState.CHECKPOINT_VERIFYING,
            StepExecutionState.BLOCKED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.CHECKPOINT_VERIFYING: frozenset(
        {
            StepExecutionState.TOOL_PREPARING,
            StepExecutionState.BLOCKED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.TOOL_PREPARING: frozenset(
        {
            StepExecutionState.TOOL_RUNNING,
            StepExecutionState.AWAITING_APPROVAL,
            StepExecutionState.BLOCKED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.TOOL_RUNNING: frozenset(
        {
            StepExecutionState.EFFECT_VERIFYING,
            StepExecutionState.RETRY_PENDING,
            StepExecutionState.ROLLBACK_PENDING,
            StepExecutionState.FAILED,
            StepExecutionState.CANCELLED,
        }
    ),
    StepExecutionState.EFFECT_VERIFYING: frozenset(
        {
            StepExecutionState.EVIDENCE_RECORDING,
            StepExecutionState.ROLLBACK_PENDING,
            StepExecutionState.ESCALATED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.EVIDENCE_RECORDING: frozenset(
        {
            StepExecutionState.SUCCEEDED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.RETRY_PENDING: frozenset(
        {
            StepExecutionState.TOOL_PREPARING,
            StepExecutionState.ROLLBACK_PENDING,
            StepExecutionState.ESCALATED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.ROLLBACK_PENDING: frozenset(
        {
            StepExecutionState.ROLLED_BACK,
            StepExecutionState.ESCALATED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.ROLLED_BACK: frozenset(
        {
            StepExecutionState.RETRY_PENDING,
            StepExecutionState.PAUSED,
            StepExecutionState.ESCALATED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.BLOCKED: frozenset(
        {
            StepExecutionState.ELIGIBILITY_CHECK,
            StepExecutionState.PAUSED,
            StepExecutionState.ESCALATED,
            StepExecutionState.CANCELLED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.AWAITING_APPROVAL: frozenset(
        {
            StepExecutionState.TOOL_PREPARING,
            StepExecutionState.PAUSED,
            StepExecutionState.CANCELLED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.PAUSED: frozenset(
        {
            StepExecutionState.ELIGIBILITY_CHECK,
            StepExecutionState.CANCELLED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.ESCALATED: frozenset(
        {
            StepExecutionState.PAUSED,
            StepExecutionState.CANCELLED,
            StepExecutionState.FAILED,
        }
    ),
    StepExecutionState.SUCCEEDED: frozenset(),
    StepExecutionState.FAILED: frozenset(),
    StepExecutionState.CANCELLED: frozenset(),
}

EXECUTION_TRANSITIONS: Final[
    Mapping[
        StepExecutionState,
        frozenset[StepExecutionState],
    ]
] = MappingProxyType(_TRANSITIONS)


def assert_execution_transition(
    current: StepExecutionState,
    target: StepExecutionState,
) -> None:
    """Raise when an execution transition is illegal."""
    if current in TERMINAL_EXECUTION_STATES:
        raise ExecutionContractError(
            f"Terminal execution cannot transition from {current.value}."
        )

    if target not in EXECUTION_TRANSITIONS[current]:
        raise ExecutionContractError(
            f"Illegal execution transition: "
            f"{current.value} -> {target.value}"
        )