from forge.autonomous_orchestration.models import OrchestrationRequest
from forge.autonomous_orchestration.session_registry import (
    InMemorySessionRegistry,
)
from forge.autonomous_orchestration.session_service import (
    MissionSessionService,
)
from forge.autonomous_orchestration.states import OrchestrationState


def test_service_creates_and_transitions_session() -> None:
    service = MissionSessionService(
        registry=InMemorySessionRegistry()
    )
    session = service.create(
        OrchestrationRequest(
            request_id="request-1",
            mission_id="mission-1",
            repository_root="repository",
            requested_by="Aerion",
        ),
        plan_id="plan-1",
        plan_version=1,
    )

    session = service.transition(
        session,
        OrchestrationState.INITIALIZING,
    )

    assert session.state is OrchestrationState.INITIALIZING
    assert session.version == 2


def test_service_marks_step_completed() -> None:
    service = MissionSessionService(
        registry=InMemorySessionRegistry()
    )
    session = service.create(
        OrchestrationRequest(
            request_id="request-1",
            mission_id="mission-1",
            repository_root="repository",
            requested_by="Aerion",
        ),
        plan_id="plan-1",
        plan_version=1,
    )
    session = service.set_current_step(session, "step-1")
    session = service.mark_step_completed(session, "step-1")

    assert session.current_step_id is None
    assert session.completed_step_ids == ("step-1",)
    assert session.execution_count == 1
    assert session.cycle_count == 1