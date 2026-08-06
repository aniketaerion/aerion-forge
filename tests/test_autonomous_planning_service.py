from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import PlanningRequest
from forge.autonomous_planning.plan_generation import (
    AutonomousPlanGenerator,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.repository import (
    InMemoryPlanningRepository,
)
from forge.autonomous_planning.service import (
    AutonomousPlanningService,
)
from forge.autonomous_planning.states import (
    PlanningIntent,
    PlanningState,
)
from forge.autonomous_planning.validation import (
    AutonomousPlanValidator,
)


def test_service_creates_valid_plan() -> None:
    policy = AutonomousPlanningPolicy()
    service = AutonomousPlanningService(
        generator=AutonomousPlanGenerator(
            policy=policy
        ),
        validator=AutonomousPlanValidator(
            policy=policy
        ),
        repository=InMemoryPlanningRepository(),
    )

    generated, validation = service.create_plan(
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
            validation_commands=("python -m pytest",),
        ),
    )

    assert validation.valid
    assert generated.plan.state is PlanningState.READY
    assert (
        service.repository.get_plan(
            generated.plan.plan_id
        )
        == generated.plan
    )