from forge.mission_runtime.models import MissionSession
from forge.mission_runtime.repository import InMemoryMissionRepository


def test_repository_round_trip() -> None:
    repository = InMemoryMissionRepository()
    session = MissionSession(
        session_id="session-1",
        request_id="request-1",
        workspace_id="workspace-1",
        repository_root="repository",
        repository_fingerprint="fingerprint",
    )

    repository.put_session(session)

    assert repository.get_session("session-1") == session