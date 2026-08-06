"""Deterministic scheduler for mission execution steps."""

from __future__ import annotations

from forge.autonomous_execution.dependency_graph import (
    validate_dependency_graph,
)
from forge.autonomous_execution.eligibility import (
    evaluate_step_eligibility,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionPlan,
    MissionStep,
)


def ordered_steps(
    plan: MissionPlan,
) -> tuple[MissionStep, ...]:
    """Return plan steps in deterministic sequence order."""
    validate_dependency_graph(plan.steps)
    return tuple(
        sorted(
            plan.steps,
            key=lambda step: (
                step.sequence,
                step.step_id,
            ),
        )
    )


def next_eligible_step(
    mission: AutonomousMission,
    plan: MissionPlan,
    *,
    completed_step_ids: frozenset[str],
) -> MissionStep | None:
    """Select the first eligible step deterministically."""
    for step in ordered_steps(plan):
        if step.step_id in completed_step_ids:
            continue

        result = evaluate_step_eligibility(
            mission,
            step,
            completed_step_ids=completed_step_ids,
        )
        if result.eligible:
            return step

    return None