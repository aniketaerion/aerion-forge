from forge.autonomous_planning.cycle_detection import (
    find_cycle,
    is_acyclic,
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


def dependency(
    dependency_id: str,
    source: str,
    target: str,
) -> PlanningDependency:
    return PlanningDependency(
        dependency_id=dependency_id,
        source_step_id=source,
        target_step_id=target,
        kind=DependencyKind.REQUIRES,
        rationale="Required ordering.",
    )


def test_cycle_is_detected() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))
    graph.add_dependency(
        dependency(
            "dependency-1",
            "step-1",
            "step-2",
        )
    )
    graph.add_dependency(
        dependency(
            "dependency-2",
            "step-2",
            "step-1",
        )
    )

    assert not is_acyclic(graph)
    assert find_cycle(graph) is not None