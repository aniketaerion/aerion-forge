"""Planning-step eligibility evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.graph import PlanningGraph


@dataclass(frozen=True, slots=True)
class StepEligibility:
    """Eligibility result for one planning step."""

    step_id: str
    eligible: bool
    unmet_prerequisites: tuple[str, ...]


def evaluate_step_eligibility(
    *,
    graph: PlanningGraph,
    step_id: str,
    completed_step_ids: tuple[str, ...],
) -> StepEligibility:
    """Evaluate whether all prerequisites are complete."""
    completed = set(completed_step_ids)
    prerequisites = graph.prerequisite_ids(step_id)
    unmet = tuple(
        step
        for step in prerequisites
        if step not in completed
    )

    return StepEligibility(
        step_id=step_id,
        eligible=not unmet,
        unmet_prerequisites=unmet,
    )


def eligible_step_ids(
    *,
    graph: PlanningGraph,
    completed_step_ids: tuple[str, ...],
) -> tuple[str, ...]:
    """Return deterministic currently eligible steps."""
    completed = set(completed_step_ids)
    values: list[str] = []

    for step in graph.steps():
        if step.step_id in completed:
            continue

        result = evaluate_step_eligibility(
            graph=graph,
            step_id=step.step_id,
            completed_step_ids=completed_step_ids,
        )

        if result.eligible:
            values.append(step.step_id)

    return tuple(values)