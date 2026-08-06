"""Autonomous execution engine enumerations."""

from __future__ import annotations

from enum import StrEnum


class StepExecutionState(StrEnum):
    """Authoritative execution states for one mission step."""

    PENDING = "pending"
    ELIGIBILITY_CHECK = "eligibility_check"
    READY = "ready"
    LEASE_ACQUIRING = "lease_acquiring"
    CHECKPOINT_VERIFYING = "checkpoint_verifying"
    TOOL_PREPARING = "tool_preparing"
    TOOL_RUNNING = "tool_running"
    EFFECT_VERIFYING = "effect_verifying"
    EVIDENCE_RECORDING = "evidence_recording"
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    AWAITING_APPROVAL = "awaiting_approval"
    RETRY_PENDING = "retry_pending"
    ROLLBACK_PENDING = "rollback_pending"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"
    ESCALATED = "escalated"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolExecutionStatus(StrEnum):
    """Tool invocation status."""

    PENDING = "pending"
    VALIDATING = "validating"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    DRY_RUN = "dry_run"


class ExecutionFailureClass(StrEnum):
    """Failure classes defined by the M5.2 architecture."""

    ELIGIBILITY_FAILURE = "eligibility_failure"
    DEPENDENCY_FAILURE = "dependency_failure"
    AUTHORITY_FAILURE = "authority_failure"
    APPROVAL_FAILURE = "approval_failure"
    LEASE_FAILURE = "lease_failure"
    CHECKPOINT_FAILURE = "checkpoint_failure"
    TOOL_RESOLUTION_FAILURE = "tool_resolution_failure"
    ARGUMENT_VALIDATION_FAILURE = "argument_validation_failure"
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_EXIT_FAILURE = "tool_exit_failure"
    SCOPE_VIOLATION = "scope_violation"
    EVIDENCE_FAILURE = "evidence_failure"
    INVARIANT_VIOLATION = "invariant_violation"
    ROLLBACK_FAILURE = "rollback_failure"


TERMINAL_EXECUTION_STATES: frozenset[StepExecutionState] = frozenset(
    {
        StepExecutionState.SUCCEEDED,
        StepExecutionState.FAILED,
        StepExecutionState.CANCELLED,
    }
)