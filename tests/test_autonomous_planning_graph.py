import pytest

from forge.autonomous_planning.errors import (
    PlanningContractError,
)
from forge.autonomous_planning.graph import PlanningGraph
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
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


def test_graph_returns_prerequisites() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))
    graph.add_dependency(
        PlanningDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            kind=DependencyKind.REQUIRES,
            rationale="Step two requires step one.",
        )
    )

    assert graph.prerequisite_ids("step-2") == (
        "step-1",
    )


def test_graph_rejects_unknown_dependency_step() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-1", 1))

    with pytest.raises(PlanningContractError):
        graph.add_dependency(
            PlanningDependency(
                dependency_id="dependency-1",
                source_step_id="missing",
                target_step_id="step-1",
                kind=DependencyKind.REQUIRES,
                rationale="Invalid dependency.",
            )
        )