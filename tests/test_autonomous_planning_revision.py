from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.revision import revise_plan
from forge.autonomous_planning.states import (
    PlanningState,
    StepKind,
)


def test_revision_increments_version() -> None:
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
                kind=StepKind.VALIDATION,
            ),
        ),
    )

    revision = revise_plan(
        plan=plan,
        rationale="Add validation evidence.",
    )

    assert revision.revised.version == 2
    assert revision.revised.plan_id != plan.plan_id
    assert (
        revision.revised.state
        is PlanningState.VALIDATING
    )