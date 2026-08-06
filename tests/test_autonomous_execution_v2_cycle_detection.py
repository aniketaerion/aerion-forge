from forge.autonomous_execution_v2.cycle_detection import (
    find_cycle,
    is_acyclic,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=step_id,
        description="Execute a repository-grounded action.",
    )


def dependency(
    dependency_id: str,
    source: str,
    target: str,
) -> ExecutionDependency:
    return ExecutionDependency(
        dependency_id=dependency_id,
        source_step_id=source,
        target_step_id=target,
        rationale="Required ordering.",
    )


def test_cycle_is_detected() -> None:
    graph = ExecutionGraph()
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