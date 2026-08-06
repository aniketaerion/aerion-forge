"""Planning graph builder from immutable plan contracts."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.cycle_detection import (
    find_cycle,
)
from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.graph import PlanningGraph
from forge.autonomous_planning.models import PlanningPlan
from forge.autonomous_planning.ordering import topological_order
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)


@dataclass(frozen=True, slots=True)
class PlanningGraphBuildResult:
    """Built graph and deterministic execution order."""

    graph: PlanningGraph
    ordered_step_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanningGraphBuilder:
    """Build and validate a planning graph."""

    policy: AutonomousPlanningPolicy

    def build(
        self,
        plan: PlanningPlan,
    ) -> PlanningGraphBuildResult:
        if len(plan.steps) > self.policy.limits.maximum_steps:
            raise PlanningContractError(
                "Plan exceeds maximum step count."
            )

        if (
            len(plan.dependencies)
            > self.policy.limits.maximum_dependencies
        ):
            raise PlanningContractError(
                "Plan exceeds maximum dependency count."
            )

        graph = PlanningGraph()

        for step in plan.steps:
            graph.add_step(step)

        for dependency in plan.dependencies:
            graph.add_dependency(dependency)

        cycle = find_cycle(graph)

        if (
            cycle is not None
            and self.policy.quality.require_dependency_acyclicity
        ):
            raise PlanningContractError(
                "Planning graph contains cycle: "
                + " -> ".join(cycle)
            )

        ordered = topological_order(graph)

        return PlanningGraphBuildResult(
            graph=graph,
            ordered_step_ids=ordered,
        )