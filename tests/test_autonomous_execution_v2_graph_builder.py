import pytest

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.graph_builder import (
    ExecutionGraphBuilder,
)
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=step_id,
        description="Execute a repository-grounded action.",
    )


def run(
    dependencies: tuple[ExecutionDependency, ...],
) -> ExecutionRun:
    return ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        steps=(
            step("step-1", 1),
            step("step-2", 2),
        ),
        dependencies=dependencies,
    )


def test_builder_returns_deterministic_order() -> None:
    result = ExecutionGraphBuilder(
        policy=AutonomousExecutionV2Policy()
    ).build(
        run(
            (
                ExecutionDependency(
                    dependency_id="dependency-1",
                    source_step_id="step-2",
                    target_step_id="step-1",
                    rationale="Step two requires step one.",
                ),
            )
        )
    )

    assert result.ordered_step_ids == (
        "step-1",
        "step-2",
    )


def test_builder_rejects_cycle() -> None:
    dependencies = (
        ExecutionDependency(
            dependency_id="dependency-1",
            source_step_id="step-1",
            target_step_id="step-2",
            rationale="Required ordering.",
        ),
        ExecutionDependency(
            dependency_id="dependency-2",
            source_step_id="step-2",
            target_step_id="step-1",
            rationale="Required ordering.",
        ),
    )

    with pytest.raises(ExecutionContractError):
        ExecutionGraphBuilder(
            policy=AutonomousExecutionV2Policy()
        ).build(run(dependencies))