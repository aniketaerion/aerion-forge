import pytest

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
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


def test_graph_returns_prerequisites() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))
    graph.add_dependency(
        ExecutionDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            rationale="Step two requires step one.",
        )
    )

    assert graph.prerequisite_ids("step-2") == (
        "step-1",
    )


def test_graph_rejects_unknown_dependency_step() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-1", 1))

    with pytest.raises(ExecutionContractError):
        graph.add_dependency(
            ExecutionDependency(
                dependency_id="dependency-1",
                source_step_id="missing",
                target_step_id="step-1",
                rationale="Invalid dependency.",
            )
        )