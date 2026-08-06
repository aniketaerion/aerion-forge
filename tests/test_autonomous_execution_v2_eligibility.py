from forge.autonomous_execution_v2.eligibility import (
    eligible_execution_step_ids,
    evaluate_execution_eligibility,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)
from forge.autonomous_execution_v2.states import (
    ExecutionStepState,
)


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=step_id,
        description="Execute a repository-grounded action.",
    )


def test_eligibility_requires_completed_prerequisite() -> None:
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

    blocked = evaluate_execution_eligibility(
        graph=graph,
        step_id="step-2",
        step_states={
            "step-1": ExecutionStepState.PENDING,
        },
    )
    ready = evaluate_execution_eligibility(
        graph=graph,
        step_id="step-2",
        step_states={
            "step-1": ExecutionStepState.SUCCEEDED,
        },
    )

    assert not blocked.eligible
    assert ready.eligible
    assert eligible_execution_step_ids(
        graph=graph,
        step_states={},
    ) == ("step-1",)