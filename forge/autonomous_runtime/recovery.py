"""Bounded recovery decision engine."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionCheckpoint,
)
from forge.autonomous_runtime.states import RecoveryAction


@dataclass(frozen=True, slots=True)
class RecoveryContext:
    """Inputs required to choose a recovery action."""

    failure_class: str
    step_attempt_number: int
    rollback_attempt_number: int
    retryable: bool
    checkpoint: MissionCheckpoint | None = None
    mission_can_replan: bool = True


@dataclass(frozen=True, slots=True)
class RecoveryEvaluation:
    """Deterministic recovery decision."""

    action: RecoveryAction
    reason: str


_FATAL_FAILURES = frozenset(
    {
        "invariant_violation",
        "rollback_failure",
        "checkpoint_corruption",
        "authority_failure",
        "approval_failure",
    }
)


def choose_recovery_action(
    mission: AutonomousMission,
    context: RecoveryContext,
) -> RecoveryEvaluation:
    """Choose a bounded recovery action from mission policy."""
    budgets = mission.request.budgets

    if context.failure_class in _FATAL_FAILURES:
        return RecoveryEvaluation(
            action=RecoveryAction.ESCALATE,
            reason="Failure class requires human escalation.",
        )

    if context.retryable and (
        context.step_attempt_number
        < budgets.maximum_attempts_per_step
    ):
        return RecoveryEvaluation(
            action=RecoveryAction.RETRY_STEP,
            reason="Retryable failure and step budget remains.",
        )

    if context.checkpoint is not None and (
        context.rollback_attempt_number
        < budgets.maximum_rollback_attempts
    ):
        return RecoveryEvaluation(
            action=RecoveryAction.ROLLBACK_STEP,
            reason="Verified rollback path should be attempted.",
        )

    if (
        context.mission_can_replan
        and mission.replan_count < budgets.maximum_replans
    ):
        return RecoveryEvaluation(
            action=RecoveryAction.REPLAN,
            reason="Retry exhausted; replan budget remains.",
        )

    return RecoveryEvaluation(
        action=RecoveryAction.ABORT,
        reason="No safe recovery budget remains.",
    )


def assert_recovery_action_allowed(
    mission: AutonomousMission,
    context: RecoveryContext,
    requested: RecoveryAction,
) -> None:
    """Raise when a requested recovery action violates policy."""
    evaluated = choose_recovery_action(mission, context)

    if evaluated.action is not requested:
        raise MissionContractError(
            "Requested recovery action is not permitted: "
            f"expected {evaluated.action.value}, got {requested.value}."
        )