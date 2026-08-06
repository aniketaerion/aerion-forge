"""Recovery decisions for M5.7 autonomous execution."""

from __future__ import annotations

from forge.autonomous_execution_v2.identifiers import deterministic_identifier
from forge.autonomous_execution_v2.models import (
    ExecutionAttempt,
    RecoveryDecision,
)
from forge.autonomous_execution_v2.policies import AutonomousExecutionV2Policy
from forge.autonomous_execution_v2.retry import evaluate_retry
from forge.autonomous_execution_v2.states import RecoveryAction


def decide_recovery(
    *,
    run_id: str,
    step_id: str,
    attempt: ExecutionAttempt,
    attempts_for_step: tuple[ExecutionAttempt, ...],
    policy: AutonomousExecutionV2Policy,
) -> RecoveryDecision:
    """Choose retry or abort after a failed attempt."""
    retry = evaluate_retry(
        attempts=attempts_for_step,
        policy=policy,
    )
    action = RecoveryAction.RETRY if retry.allowed else RecoveryAction.ABORT
    rationale = (
        retry.rationale
        if retry.allowed
        else "Execution cannot safely continue."
    )
    payload = {
        "run_id": run_id,
        "step_id": step_id,
        "attempt_id": attempt.attempt_id,
        "action": action.value,
        "rationale": rationale,
    }

    return RecoveryDecision(
        decision_id=deterministic_identifier(
            "recovery-decision-v2",
            payload,
        ),
        run_id=run_id,
        step_id=step_id,
        attempt_id=attempt.attempt_id,
        action=action,
        rationale=rationale,
    )