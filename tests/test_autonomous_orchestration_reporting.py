from pathlib import Path

from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.reporting import (
    orchestration_summary,
    render_orchestration_markdown,
    write_orchestration_report,
)
from forge.autonomous_orchestration.states import OrchestrationState


def session() -> MissionSession:
    return MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        state=OrchestrationState.PAUSED,
        current_step_id="step-1",
    )


def test_orchestration_summary_is_structured() -> None:
    summary = orchestration_summary(session())

    assert summary["session_id"] == "session-1"
    assert summary["state"] == "paused"
    assert summary["current_step_id"] == "step-1"


def test_orchestration_markdown_contains_state() -> None:
    report = render_orchestration_markdown(session())

    assert "Autonomous Mission Orchestration" in report
    assert "`paused`" in report


def test_write_orchestration_report(tmp_path: Path) -> None:
    json_path, markdown_path = write_orchestration_report(
        session(),
        tmp_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()