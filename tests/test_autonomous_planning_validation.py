from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.states import (
    PlanningRisk,
    StepKind,
)
from forge.autonomous_planning.validation import (
    AutonomousPlanValidator,
)


def test_validator_rejects_plan_without_validation_step() -> None:
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Analyse",
                description=(
                    "Analyse repository impact before changes."
                ),
                kind=StepKind.ANALYSIS,
                risk=PlanningRisk.LOW,
            ),
        ),
    )

    result = AutonomousPlanValidator(
        policy=AutonomousPlanningPolicy()
    ).validate(plan)

    assert not result.valid
    assert any(
        finding.code == "VALIDATION_STEP_MISSING"
        for finding in result.findings
    )