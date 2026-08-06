from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.repository import (
    InMemoryPlanningRepository,
)
from forge.autonomous_planning.states import StepKind


def test_repository_persists_plan() -> None:
    repository = InMemoryPlanningRepository()
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

    repository.put_plan(plan)

    assert repository.get_plan("plan-1") == plan
    assert repository.all_plans() == (plan,)