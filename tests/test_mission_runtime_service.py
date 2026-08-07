from forge.mission_runtime.models import MissionSession
from forge.mission_runtime.repository import InMemoryMissionRepository
from forge.mission_runtime.service import MissionRuntimeService
from forge.mission_runtime.states import MissionState


def test_service_transitions_session() -> None:
    repository = InMemoryMissionRepository()
    service = MissionRuntimeService(repository)
    session = MissionSession(
        session_id="session-1",
        request_id="request-1",
        workspace_id="workspace-1",
        repository_root="repository",
        repository_fingerprint="fingerprint",
    )
    service.register(session)

    updated = service.transition(
        session_id="session-1",
        target=MissionState.RESOLVING_WORKSPACE,
    )

    assert updated.state is MissionState.RESOLVING_WORKSPACE