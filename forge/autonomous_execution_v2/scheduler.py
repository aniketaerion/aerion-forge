"""Deterministic scheduler for M5.7 execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.eligibility import (
    eligible_execution_step_ids,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.ordering import topological_order
from forge.autonomous_execution_v2.states import (
    ExecutionStepState,
)


@dataclass(frozen=True, slots=True)
class ExecutionSchedule:
    """Current execution scheduling decision."""

    ordered_step_ids: tuple[str, ...]
    eligible_step_ids: tuple[str, ...]
    next_step_id: str | None


def build_execution_schedule(
    *,
    graph: ExecutionGraph,
    step_states: dict[str, ExecutionStepState],
) -> ExecutionSchedule:
    """Build deterministic execution schedule."""
    ordered = topological_order(graph)
    eligible = set(
        eligible_execution_step_ids(
            graph=graph,
            step_states=step_states,
        )
    )
    eligible_ordered = tuple(
        step_id
        for step_id in ordered
        if step_id in eligible
    )

    return ExecutionSchedule(
        ordered_step_ids=ordered,
        eligible_step_ids=eligible_ordered,
        next_step_id=(
            eligible_ordered[0]
            if eligible_ordered
            else None
        ),
    )