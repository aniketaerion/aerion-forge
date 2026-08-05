from pathlib import Path

from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
)
from forge.agent_runtime.reporting import (
    render_markdown,
    write_report_bundle,
)


def session_for() -> AgentSession:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )
    return AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.CREATED,
        stages=(stage,),
    )


def test_markdown_contains_session_status() -> None:
    rendered = render_markdown(session_for())

    assert "Unified Agent Runtime Report" in rendered
    assert "created" in rendered


def test_report_bundle_writes_files(tmp_path: Path) -> None:
    written = write_report_bundle(
        session_for(),
        tmp_path / "reports",
    )

    assert set(written) == {
        "AGENT_SESSION.json",
        "AGENT_SESSION_REPORT.md",
    }