from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import PlanningRequest
from forge.autonomous_planning.plan_generation import (
    AutonomousPlanGenerator,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.states import (
    PlanningIntent,
    PlanningState,
)


def test_generator_builds_ready_plan() -> None:
    result = AutonomousPlanGenerator(
        policy=AutonomousPlanningPolicy()
    ).generate(
        request=PlanningRequest(
            request_id="request-1",
            objective="Implement feature",
            repository_root="repository",
            intent=PlanningIntent.IMPLEMENT_FEATURE,
            acceptance_criteria=("Tests pass",),
            created_by="Aerion",
        ),
        context=PlanningContext(
            repository_root="repository",
            repository_fingerprint="fingerprint-1",
            validation_commands=(
                "python -m pytest",
            ),
        ),
    )

    assert result.plan.state is PlanningState.READY
    assert result.ordered_step_ids == tuple(
        step.step_id
        for step in result.plan.steps
    )


def test_high_risk_plan_requires_approval() -> None:
    result = AutonomousPlanGenerator(
        policy=AutonomousPlanningPolicy()
    ).generate(
        request=PlanningRequest(
            request_id="request-1",
            objective="Release production migration",
            repository_root="repository",
            intent=PlanningIntent.RELEASE,
            acceptance_criteria=("Release validated",),
            created_by="Aerion",
        ),
        context=PlanningContext(
            repository_root="repository",
            repository_fingerprint="fingerprint-1",
        ),
    )

    assert result.plan.requires_approval
    assert (
        result.plan.state
        is PlanningState.AWAITING_APPROVAL
    )