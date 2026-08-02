"""Mission Reporting CLI tests."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from forge.cli import app
from forge.config import Settings
from forge.impact.models import ImpactDecisionGeneration
from forge.mission_reporting.cli import report_app
from forge.mission_reporting.service import MissionReportingService
from forge.tasks.models import TaskGeneration
from tests.test_engineering_memory_builder import _inputs

runner = CliRunner()


def _patch_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )

    monkeypatch.setattr(
        "forge.mission_reporting.cli.Settings",
        lambda: settings,
    )


def _persist_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    _patch_settings(tmp_path, monkeypatch)

    mission, task_set, assessment = _inputs()

    memory_path = tmp_path / "memory"
    reports_path = tmp_path / "reports"
    memory_path.mkdir(parents=True, exist_ok=True)

    from forge.engineering_memory.service import EngineeringMemoryService
    from forge.impact.service import ImpactDecisionService
    from forge.impact.store import ImpactRepository
    from forge.planning.store import MissionPlanRepository
    from forge.tasks.store import TaskRepository

    MissionPlanRepository(
        memory_path / "missions.json",
        history_limit=10,
    ).save(mission)

    task_generation = TaskGeneration(
        generation_id=(f"task-generation-{task_set.task_set_fingerprint[:20]}"),
        mission_id=task_set.mission_id,
        mission_fingerprint=task_set.mission_fingerprint,
        task_set_fingerprint=task_set.task_set_fingerprint,
        task_count=len(task_set.tasks),
        statistics=task_set.statistics,
    )

    TaskRepository(
        memory_path / "tasks.json",
        history_limit=10,
    ).save(
        task_set,
        task_generation,
    )

    impact_generation = ImpactDecisionGeneration(
        generation_id=(f"impact-generation-{assessment.assessment_fingerprint[:20]}"),
        assessment_id=assessment.assessment_id,
        assessment_fingerprint=(assessment.assessment_fingerprint),
        mission_id=assessment.mission_id,
        task_set_fingerprint=(assessment.task_set_fingerprint),
        finding_count=len(assessment.findings),
    )

    ImpactRepository(
        memory_path / ImpactDecisionService.STORE_NAME,
    ).save(
        assessment,
        impact_generation,
    )

    EngineeringMemoryService(
        memory_path=memory_path,
        reports_path=reports_path,
    ).build(
        mission,
        task_set,
        assessment,
        write_reports=False,
    )

    return mission.mission_id


def test_report_help_contract() -> None:
    result = runner.invoke(report_app, ["--help"])

    assert result.exit_code == 0
    assert "Build and inspect deterministic Mission Reports." in result.stdout
    assert "build" in result.stdout
    assert "show" in result.stdout


def test_report_registered_in_root_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "report" in result.stdout


def test_build_creates_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    result = runner.invoke(
        report_app,
        ["build", mission_id],
    )

    assert result.exit_code == 0
    assert "Report ID:" in result.stdout

    for name in (
        "MISSION_REPORT.json",
        "MISSION_SUMMARY.json",
        "MISSION_TRACEABILITY.json",
        "MISSION_RISKS.json",
        "MISSION_REPORT.md",
    ):
        assert (tmp_path / "reports" / name).is_file()


def test_build_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    result = runner.invoke(
        report_app,
        ["build", mission_id, "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["report"]["mission_id"] == mission_id


def test_build_no_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    result = runner.invoke(
        report_app,
        ["build", mission_id, "--no-reports"],
    )

    assert result.exit_code == 0
    assert not (tmp_path / "reports" / "MISSION_REPORT.json").exists()


def test_build_unknown_mission_returns_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(
        report_app,
        ["build", "mission-missing"],
    )

    assert result.exit_code == 2


def test_show_latest_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    build_result = runner.invoke(
        report_app,
        ["build", mission_id],
    )
    assert build_result.exit_code == 0

    result = runner.invoke(report_app, ["show"])

    assert result.exit_code == 0
    assert "Report ID:" in result.stdout
    assert mission_id in result.stdout


def test_show_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    runner.invoke(
        report_app,
        ["build", mission_id],
    )

    result = runner.invoke(
        report_app,
        ["show", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mission_id"] == mission_id


def test_show_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    runner.invoke(
        report_app,
        ["build", mission_id],
    )

    result = runner.invoke(
        report_app,
        ["show", "--sections"],
    )

    assert result.exit_code == 0
    assert "Mission Report Sections" in result.stdout


def test_show_without_report_returns_four(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_settings(tmp_path, monkeypatch)

    result = runner.invoke(report_app, ["show"])

    assert result.exit_code == 4


def test_build_output_contains_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    result = runner.invoke(
        report_app,
        ["build", mission_id],
    )

    assert result.exit_code == 0
    assert "Status:" in result.stdout


def test_build_output_contains_task_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    result = runner.invoke(
        report_app,
        ["build", mission_id],
    )

    assert result.exit_code == 0
    assert "Tasks:" in result.stdout


def test_build_output_contains_risk_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    result = runner.invoke(
        report_app,
        ["build", mission_id],
    )

    assert result.exit_code == 0
    assert "Risks:" in result.stdout


def test_build_output_contains_traceability_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    result = runner.invoke(
        report_app,
        ["build", mission_id],
    )

    assert result.exit_code == 0
    assert "Traceability:" in result.stdout


def test_build_output_contains_fingerprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    result = runner.invoke(
        report_app,
        ["build", mission_id],
    )

    assert result.exit_code == 0
    assert "Fingerprint:" in result.stdout


def test_show_json_is_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    runner.invoke(
        report_app,
        ["build", mission_id],
    )

    first = runner.invoke(
        report_app,
        ["show", "--json"],
    )
    second = runner.invoke(
        report_app,
        ["show", "--json"],
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert first.stdout == second.stdout


def test_build_can_be_repeated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    first = runner.invoke(
        report_app,
        ["build", mission_id],
    )
    second = runner.invoke(
        report_app,
        ["build", mission_id],
    )

    assert first.exit_code == 0
    assert second.exit_code == 0


def test_report_file_matches_service_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_id = _persist_inputs(tmp_path, monkeypatch)

    result = runner.invoke(
        report_app,
        ["build", mission_id],
    )

    assert result.exit_code == 0

    report_path = tmp_path / "reports" / "MISSION_REPORT.json"
    assert report_path.is_file()

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["mission_id"] == mission_id


def test_service_constant_not_required() -> None:
    assert not hasattr(MissionReportingService, "STORE_NAME")
