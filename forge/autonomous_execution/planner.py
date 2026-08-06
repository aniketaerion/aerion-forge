"""Application service for autonomous execution planning."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.eligibility import (
    EligibilityEvaluation,
    evaluate_step_eligibility,
)
from forge.autonomous_execution.execution_plan import (
    ExecutablePlan,
    build_executable_plan,
)
from forge.autonomous_execution.scheduler import next_eligible_step
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionPlan,
    MissionStep,
)


@dataclass(frozen=True, slots=True)
class StepSelection:
    """Result of deterministic step selection."""

    step: MissionStep | None
    reason: str


class AutonomousExecutionPlanner:
    """Validate plans and select the next executable step."""

    def build(
        self,
        plan: MissionPlan,
    ) -> ExecutablePlan:
        return build_executable_plan(plan)

    def evaluate(
        self,
        mission: AutonomousMission,
        step: MissionStep,
        *,
        completed_step_ids: frozenset[str],
    ) -> EligibilityEvaluation:
        return evaluate_step_eligibility(
            mission,
            step,
            completed_step_ids=completed_step_ids,
        )

    def select_next(
        self,
        mission: AutonomousMission,
        plan: MissionPlan,
        *,
        completed_step_ids: frozenset[str],
    ) -> StepSelection:
        step = next_eligible_step(
            mission,
            plan,
            completed_step_ids=completed_step_ids,
        )

        if step is None:
            return StepSelection(
                step=None,
                reason="No eligible execution step is available.",
            )

        return StepSelection(
            step=step,
            reason="Selected first eligible step by sequence.",
        )