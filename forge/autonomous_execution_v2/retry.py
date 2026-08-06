"""Retry policy for M5.7 execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.models import ExecutionAttempt
from forge.autonomous_execution_v2.policies import AutonomousExecutionV2Policy
from forge.autonomous_execution_v2.states import ExecutionAttemptState


@dataclass(frozen=True, slots=True)
class RetryDecision:
    """Deterministic retry decision."""

    allowed: bool
    next_attempt_number: int | None
    rationale: str


def evaluate_retry(
    *,
    attempts: tuple[ExecutionAttempt, ...],
    policy: AutonomousExecutionV2Policy,
) -> RetryDecision:
    """Evaluate whether another attempt is permitted."""
    if not attempts:
        return RetryDecision(
            allowed=True,
            next_attempt_number=1,
            rationale="No prior attempts exist.",
        )

    latest = max(attempts, key=lambda item: item.attempt_number)

    if latest.state is ExecutionAttemptState.SUCCEEDED:
        return RetryDecision(
            allowed=False,
            next_attempt_number=None,
            rationale="Successful step does not require retry.",
        )

    next_number = latest.attempt_number + 1

    if next_number > policy.limits.maximum_attempts_per_step:
        return RetryDecision(
            allowed=False,
            next_attempt_number=None,
            rationale="Maximum step attempts exhausted.",
        )

    return RetryDecision(
        allowed=True,
        next_attempt_number=next_number,
        rationale="Retry permitted by bounded-attempt policy.",
    )