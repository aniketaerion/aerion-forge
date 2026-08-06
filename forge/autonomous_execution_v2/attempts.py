"""Execution-attempt lifecycle management."""

from __future__ import annotations

from datetime import UTC, datetime

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
    ExecutionStateError,
)
from forge.autonomous_execution_v2.identifiers import (
    execution_attempt_identifier,
)
from forge.autonomous_execution_v2.models import ExecutionAttempt
from forge.autonomous_execution_v2.states import (
    ExecutionAttemptState,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def create_attempt(
    *,
    run_id: str,
    step_id: str,
    attempt_number: int,
) -> ExecutionAttempt:
    """Create a deterministic execution attempt."""
    if attempt_number < 1:
        raise ExecutionContractError(
            "Attempt number must be positive."
        )

    payload = {
        "run_id": run_id,
        "step_id": step_id,
        "attempt_number": attempt_number,
    }

    return ExecutionAttempt(
        attempt_id=execution_attempt_identifier(payload),
        run_id=run_id,
        step_id=step_id,
        attempt_number=attempt_number,
    )


def start_attempt(
    attempt: ExecutionAttempt,
) -> ExecutionAttempt:
    """Move an attempt from created to running."""
    if attempt.state is not ExecutionAttemptState.CREATED:
        raise ExecutionStateError(
            "Only created attempts can be started."
        )

    return attempt.model_copy(
        update={
            "state": ExecutionAttemptState.RUNNING,
            "started_at": utc_now(),
        }
    )


def complete_attempt(
    attempt: ExecutionAttempt,
    *,
    succeeded: bool,
    tool_invocation_ids: tuple[str, ...],
    failure_reason: str | None = None,
) -> ExecutionAttempt:
    """Complete a running execution attempt."""
    if attempt.state is not ExecutionAttemptState.RUNNING:
        raise ExecutionStateError(
            "Only running attempts can be completed."
        )

    if not succeeded and not failure_reason:
        raise ExecutionContractError(
            "Failed attempt requires a failure reason."
        )

    return attempt.model_copy(
        update={
            "state": (
                ExecutionAttemptState.SUCCEEDED
                if succeeded
                else ExecutionAttemptState.FAILED
            ),
            "tool_invocation_ids": tool_invocation_ids,
            "failure_reason": failure_reason,
            "completed_at": utc_now(),
        }
    )