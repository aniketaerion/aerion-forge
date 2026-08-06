"""Execution-step eligibility evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.states import (
    ExecutionStepState,
)


@dataclass(frozen=True, slots=True)
class ExecutionEligibility:
    """Eligibility result for one execution step."""

    step_id: str
    eligible: bool
    unmet_prerequisites: tuple[str, ...]
    blocking_steps: tuple[str, ...]


def evaluate_execution_eligibility(
    *,
    graph: ExecutionGraph,
    step_id: str,
    step_states: dict[str, ExecutionStepState],
) -> ExecutionEligibility:
    """Evaluate whether a step may be scheduled."""
    prerequisites = graph.prerequisite_ids(step_id)
    unmet = tuple(
        prerequisite_id
        for prerequisite_id in prerequisites
        if step_states.get(prerequisite_id)
        is not ExecutionStepState.SUCCEEDED
    )
    blocking = tuple(
        prerequisite_id
        for prerequisite_id in prerequisites
        if step_states.get(prerequisite_id)
        in {
            ExecutionStepState.FAILED,
            ExecutionStepState.BLOCKED,
            ExecutionStepState.CANCELLED,
        }
    )

    return ExecutionEligibility(
        step_id=step_id,
        eligible=not unmet,
        unmet_prerequisites=unmet,
        blocking_steps=blocking,
    )


def eligible_execution_step_ids(
    *,
    graph: ExecutionGraph,
    step_states: dict[str, ExecutionStepState],
) -> tuple[str, ...]:
    """Return deterministic currently eligible step IDs."""
    values: list[str] = []

    for step in graph.steps():
        state = step_states.get(
            step.step_id,
            step.state,
        )

        if state in {
            ExecutionStepState.SUCCEEDED,
            ExecutionStepState.RUNNING,
            ExecutionStepState.SKIPPED,
            ExecutionStepState.CANCELLED,
        }:
            continue

        result = evaluate_execution_eligibility(
            graph=graph,
            step_id=step.step_id,
            step_states=step_states,
        )

        if result.eligible:
            values.append(step.step_id)

    return tuple(values)