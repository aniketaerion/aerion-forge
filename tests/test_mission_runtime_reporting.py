from forge.mission_runtime.models import MissionSession
from forge.mission_runtime.reporting import build_mission_report


def test_reporting_uses_session_state() -> None:
    session = MissionSession(
        session_id="session-1",
        request_id="request-1",
        workspace_id="workspace-1",
        repository_root="repository",
        repository_fingerprint="fingerprint",
        selected_capabilities=("safe-code-editing",),
    )

    report = build_mission_report(session)

    assert report.session_id == "session-1"
    assert report.state == "created"
    assert report.selected_capabilities == ("safe-code-editing",)