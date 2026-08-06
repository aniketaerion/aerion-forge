"""Bounded orchestration recovery decisions."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)
from forge.autonomous_orchestration.states import OrchestrationState


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    """Bounded recovery decision for a failed step."""

    target_state: OrchestrationState
    action: str
    allowed: bool
    reason: str


def decide_recovery(
    session: MissionSession,
    policy: AutonomousOrchestrationPolicy,
) -> RecoveryDecision:
    """Select retry, rollback, replan, or escalation deterministically."""
    budgets = policy.budgets

    if session.retry_count < budgets.maximum_retries:
        return RecoveryDecision(
            target_state=OrchestrationState.RETRY_PENDING,
            action="retry",
            allowed=True,
            reason="Retry budget remains.",
        )

    if session.rollback_count < budgets.maximum_rollbacks:
        return RecoveryDecision(
            target_state=OrchestrationState.ROLLBACK_PENDING,
            action="rollback",
            allowed=True,
            reason="Retry budget exhausted; rollback budget remains.",
        )

    if session.replan_count < budgets.maximum_replans:
        return RecoveryDecision(
            target_state=OrchestrationState.REPLAN_PENDING,
            action="replan",
            allowed=True,
            reason="Retry and rollback budgets exhausted; replan remains.",
        )

    return RecoveryDecision(
        target_state=OrchestrationState.ESCALATED,
        action="escalate",
        allowed=False,
        reason="All bounded recovery budgets are exhausted.",
    )