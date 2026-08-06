from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)
from forge.autonomous_execution_v2.scheduler import (
    build_execution_schedule,
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


def test_scheduler_selects_first_eligible_step() -> None:
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

    schedule = build_execution_schedule(
        graph=graph,
        step_states={
            "step-1": ExecutionStepState.PENDING,
            "step-2": ExecutionStepState.PENDING,
        },
    )

    assert schedule.next_step_id == "step-1"
    assert schedule.eligible_step_ids == ("step-1",)