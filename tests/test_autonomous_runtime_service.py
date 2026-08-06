from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.service import (
    AutonomousLifecycleService,
    MissionTransitionRequest,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Control mission lifecycle.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def test_service_exposes_available_transitions() -> None:
    service = AutonomousLifecycleService()

    assert MissionState.QUALIFYING in service.available_transitions(
        mission()
    )


def test_service_applies_transition_request() -> None:
    service = AutonomousLifecycleService()

    updated = service.transition(
        mission(),
        MissionTransitionRequest(
            target=MissionState.QUALIFYING,
        ),
    )

    assert updated.state is MissionState.QUALIFYING
    assert updated.version == 2