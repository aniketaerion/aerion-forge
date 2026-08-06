import pytest

from forge.autonomous_planning.errors import (
    PlanningContractError,
)
from forge.autonomous_planning.graph import PlanningGraph
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
)
from forge.autonomous_planning.ordering import (
    topological_order,
)
from forge.autonomous_planning.states import (
    DependencyKind,
    StepKind,
)


def step(step_id: str, sequence: int) -> PlanningStep:
    return PlanningStep(
        step_id=step_id,
        sequence=sequence,
        name=step_id,
        description="Perform a repository-grounded action.",
        kind=StepKind.ANALYSIS,
    )


def test_order_respects_dependencies() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-2", 2))
    graph.add_step(step("step-1", 1))
    graph.add_dependency(
        PlanningDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            kind=DependencyKind.REQUIRES,
            rationale="Step two requires step one.",
        )
    )

    assert topological_order(graph) == (
        "step-1",
        "step-2",
    )


def test_order_rejects_cycle() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))

    for dependency_id, source, target in (
        ("dependency-1", "step-1", "step-2"),
        ("dependency-2", "step-2", "step-1"),
    ):
        graph.add_dependency(
            PlanningDependency(
                dependency_id=dependency_id,
                source_step_id=source,
                target_step_id=target,
                kind=DependencyKind.REQUIRES,
                rationale="Required ordering.",
            )
        )

    with pytest.raises(PlanningContractError):
        topological_order(graph)