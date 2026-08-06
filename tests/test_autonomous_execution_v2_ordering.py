import pytest

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)
from forge.autonomous_execution_v2.ordering import (
    topological_order,
)


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=step_id,
        description="Execute a repository-grounded action.",
    )


def test_order_respects_dependencies() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-2", 2))
    graph.add_step(step("step-1", 1))
    graph.add_dependency(
        ExecutionDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            rationale="Step two requires step one.",
        )
    )

    assert topological_order(graph) == (
        "step-1",
        "step-2",
    )


def test_order_rejects_cycle() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))

    for dependency_id, source, target in (
        ("dependency-1", "step-1", "step-2"),
        ("dependency-2", "step-2", "step-1"),
    ):
        graph.add_dependency(
            ExecutionDependency(
                dependency_id=dependency_id,
                source_step_id=source,
                target_step_id=target,
                rationale="Required ordering.",
            )
        )

    with pytest.raises(ExecutionContractError):
        topological_order(graph)