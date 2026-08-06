"""Deterministic topological ordering for M5.7."""

from __future__ import annotations

import heapq

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph


def topological_order(
    graph: ExecutionGraph,
) -> tuple[str, ...]:
    """Return a stable dependency-respecting order."""
    steps = {
        step.step_id: step
        for step in graph.steps()
    }
    indegree = {
        step_id: 0
        for step_id in steps
    }
    dependents: dict[str, list[str]] = {
        step_id: []
        for step_id in steps
    }

    for dependency in graph.dependencies():
        indegree[dependency.source_step_id] += 1
        dependents[dependency.target_step_id].append(
            dependency.source_step_id
        )

    ready: list[tuple[int, str]] = []

    for step_id, degree in indegree.items():
        if degree == 0:
            heapq.heappush(
                ready,
                (
                    steps[step_id].sequence,
                    step_id,
                ),
            )

    ordered: list[str] = []

    while ready:
        _, step_id = heapq.heappop(ready)
        ordered.append(step_id)

        for dependent_id in sorted(
            dependents[step_id]
        ):
            indegree[dependent_id] -= 1

            if indegree[dependent_id] == 0:
                heapq.heappush(
                    ready,
                    (
                        steps[dependent_id].sequence,
                        dependent_id,
                    ),
                )

    if len(ordered) != len(steps):
        raise ExecutionContractError(
            "Execution graph contains a dependency cycle."
        )

    return tuple(ordered)