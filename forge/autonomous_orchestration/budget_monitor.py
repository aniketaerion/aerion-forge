"""Bounded orchestration budget checks."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)


@dataclass(frozen=True, slots=True)
class BudgetEvaluation:
    """Result of orchestration-budget evaluation."""

    allowed: bool
    exhausted: tuple[str, ...]


def evaluate_budgets(
    session: MissionSession,
    policy: AutonomousOrchestrationPolicy,
) -> BudgetEvaluation:
    """Evaluate all bounded orchestration counters."""
    exhausted: list[str] = []
    budgets = policy.budgets

    if session.cycle_count >= budgets.maximum_cycles:
        exhausted.append("maximum_cycles")

    if session.execution_count >= budgets.maximum_step_executions:
        exhausted.append("maximum_step_executions")

    if session.retry_count >= budgets.maximum_retries:
        exhausted.append("maximum_retries")

    if session.rollback_count >= budgets.maximum_rollbacks:
        exhausted.append("maximum_rollbacks")

    if session.replan_count >= budgets.maximum_replans:
        exhausted.append("maximum_replans")

    return BudgetEvaluation(
        allowed=not exhausted,
        exhausted=tuple(exhausted),
    )