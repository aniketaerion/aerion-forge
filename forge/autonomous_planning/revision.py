"""Immutable planning-plan revision support."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.identifiers import (
    planning_plan_identifier,
)
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.states import PlanningState


@dataclass(frozen=True, slots=True)
class PlanRevision:
    """Previous and revised immutable planning plans."""

    previous: PlanningPlan
    revised: PlanningPlan
    rationale: str


def revise_plan(
    *,
    plan: PlanningPlan,
    steps: tuple[PlanningStep, ...] | None = None,
    dependencies: tuple[PlanningDependency, ...] | None = None,
    warnings: tuple[str, ...] | None = None,
    rationale: str,
) -> PlanRevision:
    """Create the next immutable version of a plan."""
    if not rationale.strip():
        raise PlanningContractError(
            "Plan revision rationale cannot be empty."
        )

    revised_steps = steps or plan.steps
    revised_dependencies = (
        dependencies
        if dependencies is not None
        else plan.dependencies
    )
    revised_warnings = (
        warnings
        if warnings is not None
        else plan.warnings
    )
    next_version = plan.version + 1

    payload = {
        "request_id": plan.request_id,
        "version": next_version,
        "steps": tuple(
            step.step_id
            for step in revised_steps
        ),
        "dependencies": tuple(
            dependency.dependency_id
            for dependency in revised_dependencies
        ),
        "rationale": rationale,
    }

    revised = plan.model_copy(
        update={
            "plan_id": planning_plan_identifier(payload),
            "version": next_version,
            "state": PlanningState.VALIDATING,
            "steps": revised_steps,
            "dependencies": revised_dependencies,
            "warnings": revised_warnings,
        }
    )

    return PlanRevision(
        previous=plan,
        revised=revised,
        rationale=rationale,
    )