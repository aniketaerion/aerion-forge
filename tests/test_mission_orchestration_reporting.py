import json
from datetime import UTC, datetime
from pathlib import Path

from forge.mission_orchestration.models import MissionExecution
from forge.mission_orchestration.reporting import (
    build_mission_report,
    render_markdown,
    write_report_bundle,
)
from forge.mission_orchestration.service import MissionOrchestrationService


def execution_for(tmp_path: Path) -> MissionExecution:
    (tmp_path / "sample.py").write_bytes(b"print('ok')\n")
    service = MissionOrchestrationService()
    request = service.create_request(
        repository_root=tmp_path,
        objective="Report mission",
        requested_paths=("sample.py",),
    )
    execution = service.create_execution(request)
    return service.run_next(execution)


def test_build_report_is_deterministic(tmp_path: Path) -> None:
    execution = execution_for(tmp_path)
    started = datetime(2026, 1, 1, tzinfo=UTC)

    first = build_mission_report(execution, started_at=started)
    second = build_mission_report(execution, started_at=started)

    assert first.report_id == second.report_id


def test_markdown_contains_stage_timeline(tmp_path: Path) -> None:
    report = build_mission_report(
        execution_for(tmp_path),
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    rendered = render_markdown(report)

    assert "Engineering Mission Report" in rendered
    assert "mission_validation" in rendered


def test_report_bundle_writes_json_and_markdown(tmp_path: Path) -> None:
    report = build_mission_report(
        execution_for(tmp_path),
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    written = write_report_bundle(report, tmp_path / "reports")

    assert set(written) == {
        "MISSION_ORCHESTRATION_REPORT.json",
        "MISSION_ORCHESTRATION_REPORT.md",
    }
    payload = json.loads(
        written["MISSION_ORCHESTRATION_REPORT.json"].read_text(
            encoding="utf-8"
        )
    )
    assert payload["mission_id"] == report.mission_id