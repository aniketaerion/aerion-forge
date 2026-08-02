"""Impact Decision CLI tests."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import forge.impact.cli as impact_cli
from forge.cli import app
from forge.impact.models import ImpactAssessment
from forge.impact.query import ImpactQuery
from forge.impact.service import ImpactDecisionService
from forge.impact.store import ImpactRepository
from forge.planning.models import MissionPlan, MissionPlanStore, MissionWorkstream
from forge.planning.query import MissionPlanQuery
from forge.tasks.decomposer import decompose_mission
from forge.tasks.models import (
    TaskGeneration,
    TaskSet,
    TaskStore,
)
from forge.tasks.query import TaskQuery
from tests.test_task_decomposition import _mission

runner = CliRunner()


def _inputs() -> tuple[MissionPlan, TaskSet]:
    mission = _mission(
        workstreams=(
            MissionWorkstream(
                workstream_id="workstream-impact-cli",
                name="Build Impact CLI",
                objective="Build the deterministic Impact CLI.",
                expected_outputs=("CLI", "Tests"),
            ),
        )
    )
    task_set = decompose_mission(mission)
    return mission, task_set


def _task_query(task_set: TaskSet) -> TaskQuery:
    generation = TaskGeneration(
        generation_id=(f"task-generation-{task_set.task_set_fingerprint[:20]}"),
        mission_id=task_set.mission_id,
        mission_fingerprint=task_set.mission_fingerprint,
        task_set_fingerprint=task_set.task_set_fingerprint,
        task_count=len(task_set.tasks),
        statistics=task_set.statistics,
    )

    return TaskQuery(
        TaskStore(
            tasks={task.task_id: task for task in task_set.tasks},
            generations={
                task_set.mission_id: generation,
            },
        )
    )


def _prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[MissionPlan, TaskSet, ImpactDecisionService]:
    mission, task_set = _inputs()

    mission_query = MissionPlanQuery(MissionPlanStore(missions={mission.mission_id: mission}))
    task_query = _task_query(task_set)
    service = ImpactDecisionService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )

    monkeypatch.setattr(
        impact_cli,
        "_mission_query",
        lambda settings: mission_query,
    )
    monkeypatch.setattr(
        impact_cli,
        "_task_query",
        lambda settings: task_query,
    )
    monkeypatch.setattr(
        impact_cli,
        "_service",
        lambda settings: service,
    )

    return mission, task_set, service


def _persist_assessment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> ImpactAssessment:
    mission, task_set, service = _prepare(
        tmp_path,
        monkeypatch,
    )
    result = service.assess(
        mission,
        task_set,
        write_reports=False,
    )

    query = ImpactQuery(ImpactRepository(tmp_path / "memory" / "impact-decisions.json").load())

    monkeypatch.setattr(
        impact_cli,
        "_impact_query",
        lambda settings: query,
    )

    return result.assessment


def test_impact_help_contract() -> None:
    result = runner.invoke(app, ["impact", "--help"])

    assert result.exit_code == 0
    assert "assess" in result.stdout
    assert "list" in result.stdout
    assert "show" in result.stdout


def test_impact_registered_in_root_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "impact" in result.stdout


def test_assess_uses_persisted_mission_and_tasks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _ = _prepare(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["impact", "assess", mission.mission_id],
    )

    assert result.exit_code == 0
    assert "Assessment ID" in result.stdout
    assert mission.mission_id in result.stdout
    assert (tmp_path / "memory" / "impact-decisions.json").is_file()


def test_assess_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _ = _prepare(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "impact",
            "assess",
            mission.mission_id,
            "--json",
            "--no-reports",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["assessment"]["mission_id"] == mission.mission_id


def test_assess_no_persist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _ = _prepare(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "impact",
            "assess",
            mission.mission_id,
            "--no-persist",
            "--no-reports",
        ],
    )

    assert result.exit_code == 0
    assert not (tmp_path / "memory" / "impact-decisions.json").exists()


def test_assess_no_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _ = _prepare(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "impact",
            "assess",
            mission.mission_id,
            "--no-reports",
        ],
    )

    assert result.exit_code == 0
    assert not (tmp_path / "reports").exists()


def test_list_table_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = _persist_assessment(
        tmp_path,
        monkeypatch,
    )

    result = runner.invoke(app, ["impact", "list"])

    assert result.exit_code == 0
    assert "Impact Assessments" in result.stdout
    assert assessment.mission_id[:10] in result.stdout


def test_list_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = _persist_assessment(
        tmp_path,
        monkeypatch,
    )

    result = runner.invoke(
        app,
        ["impact", "list", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["assessment_id"] == assessment.assessment_id


def test_list_mission_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = _persist_assessment(
        tmp_path,
        monkeypatch,
    )

    result = runner.invoke(
        app,
        [
            "impact",
            "list",
            "--mission",
            assessment.mission_id,
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert len(json.loads(result.stdout)) == 1


def test_list_status_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = _persist_assessment(
        tmp_path,
        monkeypatch,
    )

    result = runner.invoke(
        app,
        [
            "impact",
            "list",
            "--status",
            assessment.status.value,
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert len(json.loads(result.stdout)) == 1


def test_list_severity_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = _persist_assessment(
        tmp_path,
        monkeypatch,
    )

    result = runner.invoke(
        app,
        [
            "impact",
            "list",
            "--severity",
            assessment.overall_severity.value,
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert len(json.loads(result.stdout)) == 1


def test_show_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = _persist_assessment(
        tmp_path,
        monkeypatch,
    )

    result = runner.invoke(
        app,
        ["impact", "show", assessment.assessment_id],
    )

    assert result.exit_code == 0
    assert assessment.assessment_id in result.stdout
    assert "Validation requirements" in result.stdout


def test_show_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assessment = _persist_assessment(
        tmp_path,
        monkeypatch,
    )

    result = runner.invoke(
        app,
        [
            "impact",
            "show",
            assessment.assessment_id,
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["assessment_id"] == assessment.assessment_id


def test_unknown_mission_returns_exit_code_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission_query = MissionPlanQuery(MissionPlanStore())

    monkeypatch.setattr(
        impact_cli,
        "_mission_query",
        lambda settings: mission_query,
    )
    monkeypatch.setattr(
        impact_cli,
        "_task_query",
        lambda settings: TaskQuery(TaskStore()),
    )

    result = runner.invoke(
        app,
        ["impact", "assess", "mission-missing"],
    )

    assert result.exit_code == 2


def test_unknown_assessment_returns_exit_code_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        impact_cli,
        "_impact_query",
        lambda settings: ImpactQuery(
            ImpactRepository(Path(".test-tmp-impact-missing.json")).load()
        ),
    )

    result = runner.invoke(
        app,
        ["impact", "show", "impact-missing"],
    )

    assert result.exit_code == 2


def test_invalid_status_returns_exit_code_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        impact_cli,
        "_impact_query",
        lambda settings: ImpactQuery(ImpactRepository(Path(".test-tmp-impact-status.json")).load()),
    )

    result = runner.invoke(
        app,
        [
            "impact",
            "list",
            "--status",
            "not-a-status",
        ],
    )

    assert result.exit_code == 2


def test_invalid_severity_returns_exit_code_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        impact_cli,
        "_impact_query",
        lambda settings: ImpactQuery(
            ImpactRepository(Path(".test-tmp-impact-severity.json")).load()
        ),
    )

    result = runner.invoke(
        app,
        [
            "impact",
            "list",
            "--severity",
            "not-a-severity",
        ],
    )

    assert result.exit_code == 2
