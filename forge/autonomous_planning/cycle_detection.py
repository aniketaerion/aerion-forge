"""Cycle detection for planning graphs."""

from __future__ import annotations

from forge.autonomous_planning.graph import PlanningGraph


def find_cycle(
    graph: PlanningGraph,
) -> tuple[str, ...] | None:
    """Return one deterministic cycle, if present."""
    adjacency = {
        step.step_id: graph.prerequisite_ids(step.step_id)
        for step in graph.steps()
    }
    visited: set[str] = set()
    active: list[str] = []
    active_set: set[str] = set()

    def visit(step_id: str) -> tuple[str, ...] | None:
        if step_id in active_set:
            start = active.index(step_id)
            return tuple([*active[start:], step_id])

        if step_id in visited:
            return None

        active.append(step_id)
        active_set.add(step_id)

        for prerequisite in adjacency[step_id]:
            cycle = visit(prerequisite)
            if cycle is not None:
                return cycle

        active.pop()
        active_set.remove(step_id)
        visited.add(step_id)
        return None

    for step_id in sorted(adjacency):
        cycle = visit(step_id)
        if cycle is not None:
            return cycle

    return None


def is_acyclic(graph: PlanningGraph) -> bool:
    """Return whether the planning graph is acyclic."""
    return find_cycle(graph) is None