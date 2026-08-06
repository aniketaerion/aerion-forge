import pytest

from forge.autonomous_planning.errors import (
    PlanningContractError,
)
from forge.autonomous_planning.graph_builder import (
    PlanningGraphBuilder,
)
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
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


def test_builder_returns_deterministic_order() -> None:
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Plan.",
        steps=(
            step("step-1", 1),
            step("step-2", 2),
        ),
        dependencies=(
            PlanningDependency(
                dependency_id="dependency-1",
                source_step_id="step-2",
                target_step_id="step-1",
                kind=DependencyKind.REQUIRES,
                rationale="Step two requires step one.",
            ),
        ),
    )

    result = PlanningGraphBuilder(
        policy=AutonomousPlanningPolicy()
    ).build(plan)

    assert result.ordered_step_ids == (
        "step-1",
        "step-2",
    )


def test_builder_rejects_cycle() -> None:
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Plan.",
        steps=(
            step("step-1", 1),
            step("step-2", 2),
        ),
        dependencies=(
            PlanningDependency(
                dependency_id="dependency-1",
                source_step_id="step-1",
                target_step_id="step-2",
                kind=DependencyKind.REQUIRES,
                rationale="Required ordering.",
            ),
            PlanningDependency(
                dependency_id="dependency-2",
                source_step_id="step-2",
                target_step_id="step-1",
                kind=DependencyKind.REQUIRES,
                rationale="Required ordering.",
            ),
        ),
    )

    with pytest.raises(PlanningContractError):
        PlanningGraphBuilder(
            policy=AutonomousPlanningPolicy()
        ).build(plan)