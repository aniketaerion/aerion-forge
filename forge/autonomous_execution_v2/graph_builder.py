"""Execution graph construction from execution runs."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.cycle_detection import (
    find_cycle,
)
from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import ExecutionRun
from forge.autonomous_execution_v2.ordering import (
    topological_order,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)


@dataclass(frozen=True, slots=True)
class ExecutionGraphBuildResult:
    """Built graph and deterministic order."""

    graph: ExecutionGraph
    ordered_step_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutionGraphBuilder:
    """Build and validate an execution graph."""

    policy: AutonomousExecutionV2Policy

    def build(
        self,
        run: ExecutionRun,
    ) -> ExecutionGraphBuildResult:
        if len(run.steps) > self.policy.limits.maximum_steps:
            raise ExecutionContractError(
                "Execution run exceeds maximum step count."
            )

        graph = ExecutionGraph()

        for step in run.steps:
            graph.add_step(step)

        for dependency in run.dependencies:
            graph.add_dependency(dependency)

        cycle = find_cycle(graph)

        if cycle is not None:
            raise ExecutionContractError(
                "Execution graph contains cycle: "
                + " -> ".join(cycle)
            )

        return ExecutionGraphBuildResult(
            graph=graph,
            ordered_step_ids=topological_order(graph),
        )