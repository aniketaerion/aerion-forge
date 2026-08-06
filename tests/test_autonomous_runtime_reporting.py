from pathlib import Path

from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.reporting import (
    mission_summary,
    render_mission_markdown,
    write_mission_report,
)
from forge.autonomous_runtime.states import AuthorityLevel


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Report mission state.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A1_PLAN,
            requested_by="Aerion",
        ),
    )


def test_mission_summary_is_structured() -> None:
    summary = mission_summary(mission())

    assert summary["mission_id"] == "mission-1"
    assert summary["state"] == "received"
    assert "qualifying" in summary["available_transitions"]


def test_markdown_report_contains_state() -> None:
    report = render_mission_markdown(mission())

    assert "Autonomous Mission" in report
    assert "`received`" in report


def test_write_mission_report(tmp_path: Path) -> None:
    json_path, markdown_path = write_mission_report(
        mission(),
        tmp_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()