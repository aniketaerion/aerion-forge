"""Step eligibility evaluation for autonomous execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.dependency_graph import (
    evaluate_dependencies,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionStep,
)
from forge.autonomous_runtime.states import (
    MissionState,
    StepStatus,
)


@dataclass(frozen=True, slots=True)
class EligibilityEvaluation:
    """Deterministic step eligibility result."""

    eligible: bool
    reasons: tuple[str, ...]


def evaluate_step_eligibility(
    mission: AutonomousMission,
    step: MissionStep,
    *,
    completed_step_ids: frozenset[str],
) -> EligibilityEvaluation:
    """Evaluate whether a step can enter execution."""
    reasons: list[str] = []

    if mission.state is not MissionState.EXECUTING:
        reasons.append("Mission is not in executing state.")

    if step.status not in {
        StepStatus.PENDING,
        StepStatus.READY,
    }:
        reasons.append(
            f"Step status is not executable: {step.status.value}."
        )

    dependencies = evaluate_dependencies(
        step,
        completed_step_ids=completed_step_ids,
    )
    if not dependencies.satisfied:
        reasons.append(
            "Dependencies incomplete: "
            + ", ".join(dependencies.missing_dependencies)
        )

    if (
        step.required_authority
        > mission.granted_authority
    ):
        reasons.append(
            "Step authority exceeds mission grant."
        )

    return EligibilityEvaluation(
        eligible=not reasons,
        reasons=tuple(reasons),
    )