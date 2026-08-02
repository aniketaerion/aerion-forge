"""Engineering Memory CLI tests."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import forge.engineering_memory.cli as memory_cli
from forge.cli import app
from forge.engineering_memory.models import EngineeringMemoryResult
from forge.engineering_memory.query import EngineeringMemoryQuery
from forge.engineering_memory.service import EngineeringMemoryService
from forge.impact.models import ImpactAssessment, ImpactDecisionStore
from forge.impact.query import ImpactQuery
from forge.planning.models import MissionPlan, MissionPlanStore
from forge.planning.query import MissionPlanQuery
from forge.tasks.models import TaskGeneration, TaskSet, TaskStore
from forge.tasks.query import TaskQuery
from tests.test_engineering_memory_builder import _inputs

runner = CliRunner()


def _task_query(task_set: TaskSet) -> TaskQuery:
    generation = TaskGeneration(
        generation_id=f"task-generation-{task_set.task_set_fingerprint[:20]}",
        mission_id=task_set.mission_id,
        mission_fingerprint=task_set.mission_fingerprint,
        task_set_fingerprint=task_set.task_set_fingerprint,
        task_count=len(task_set.tasks),
        statistics=task_set.statistics,
    )
    return TaskQuery(
        TaskStore(
            tasks={task.task_id: task for task in task_set.tasks},
            generations={task_set.mission_id: generation},
        )
    )


def _prepare(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[MissionPlan, TaskSet, EngineeringMemoryService]:
    mission, task_set, assessment = _inputs()
    mission_query = MissionPlanQuery(MissionPlanStore(missions={mission.mission_id: mission}))
    task_query = _task_query(task_set)
    impact_query = ImpactQuery(
        ImpactDecisionStore(
            assessments={assessment.assessment_id: assessment},
        )
    )
    service = EngineeringMemoryService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )

    monkeypatch.setattr(memory_cli, "_mission_query", lambda settings: mission_query)
    monkeypatch.setattr(memory_cli, "_task_query", lambda settings: task_query)
    monkeypatch.setattr(memory_cli, "_impact_query", lambda settings: impact_query)
    monkeypatch.setattr(memory_cli, "_service", lambda settings: service)

    return mission, task_set, service


def _persist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[MissionPlan, TaskSet, ImpactAssessment, EngineeringMemoryResult]:
    mission, task_set, service = _prepare(tmp_path, monkeypatch)
    _, _, assessment = _inputs()
    result = service.build(
        mission,
        task_set,
        assessment,
        write_reports=False,
    )
    query = EngineeringMemoryQuery(service.repository.load())
    monkeypatch.setattr(memory_cli, "_memory_query", lambda settings: query)
    return mission, task_set, assessment, result


def test_memory_help_contract() -> None:
    result = runner.invoke(app, ["memory", "--help"])

    assert result.exit_code == 0
    assert "build" in result.stdout
    assert "list" in result.stdout
    assert "show" in result.stdout


def test_memory_registered_in_root_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "memory" in result.stdout


def test_build_uses_persisted_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _ = _prepare(tmp_path, monkeypatch)

    result = runner.invoke(app, ["memory", "build", mission.mission_id])

    assert result.exit_code == 0
    assert "Engineering Memory" in result.stdout
    assert (tmp_path / "memory" / "engineering-memory.json").is_file()


def test_build_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _ = _prepare(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["memory", "build", mission.mission_id, "--json", "--no-reports"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["records"]) == 3
    assert payload["generation"]["record_count"] == 3


def test_build_no_persist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _ = _prepare(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "memory",
            "build",
            mission.mission_id,
            "--no-persist",
            "--no-reports",
        ],
    )

    assert result.exit_code == 0
    assert not (tmp_path / "memory" / "engineering-memory.json").exists()


def test_build_no_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _ = _prepare(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["memory", "build", mission.mission_id, "--no-reports"],
    )

    assert result.exit_code == 0
    assert not (tmp_path / "reports").exists()


def test_list_table_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _, result_data = _persist(tmp_path, monkeypatch)

    result = runner.invoke(app, ["memory", "list"])

    assert result.exit_code == 0
    assert "Engineering Memory" in result.stdout
    assert result_data.records[0].memory_id[:12] in result.stdout


def test_list_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _persist(tmp_path, monkeypatch)

    result = runner.invoke(app, ["memory", "list", "--json"])

    assert result.exit_code == 0
    assert len(json.loads(result.stdout)) == 3


def test_list_mission_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _, _ = _persist(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["memory", "list", "--mission", mission.mission_id, "--json"],
    )

    assert result.exit_code == 0
    assert len(json.loads(result.stdout)) == 3


def test_list_task_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, task_set, _, _ = _persist(tmp_path, monkeypatch)
    task_id = task_set.tasks[0].task_id

    result = runner.invoke(
        app,
        ["memory", "list", "--task", task_id, "--json"],
    )

    assert result.exit_code == 0
    assert len(json.loads(result.stdout)) == 2


def test_list_assessment_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, assessment, _ = _persist(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "memory",
            "list",
            "--assessment",
            assessment.assessment_id,
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 1
    assert payload[0]["memory_type"] == "decision"


def test_list_capability_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _, result_data = _persist(tmp_path, monkeypatch)
    record = result_data.records[0]
    capability_id = record.capability_ids[0]

    result = runner.invoke(
        app,
        [
            "memory",
            "list",
            "--capability",
            capability_id,
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert all(capability_id in item["capability_ids"] for item in payload)


def test_list_milestone_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _, result_data = _persist(tmp_path, monkeypatch)
    record = next(item for item in result_data.records if item.milestones)
    milestone = record.milestones[0]

    result = runner.invoke(
        app,
        ["memory", "list", "--milestone", milestone, "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert all(milestone in item["milestones"] for item in payload)


def test_list_type_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _persist(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["memory", "list", "--type", "decision", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 1
    assert payload[0]["memory_type"] == "decision"


def test_list_tag_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _, result_data = _persist(tmp_path, monkeypatch)
    record = next(item for item in result_data.records if item.tags)
    tag = record.tags[0]

    result = runner.invoke(
        app,
        ["memory", "list", "--tag", tag, "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload
    assert all(tag in item["tags"] for item in payload)


def test_invalid_type_returns_exit_code_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _persist(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["memory", "list", "--type", "not-a-memory-type"],
    )

    assert result.exit_code == 2


def test_show_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _, result_data = _persist(tmp_path, monkeypatch)
    memory_id = result_data.records[0].memory_id

    result = runner.invoke(app, ["memory", "show", memory_id])

    assert result.exit_code == 0
    assert memory_id in result.stdout
    assert "Retention" in result.stdout


def test_show_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _, result_data = _persist(tmp_path, monkeypatch)
    memory_id = result_data.records[0].memory_id

    result = runner.invoke(
        app,
        ["memory", "show", memory_id, "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["memory_id"] == memory_id


def test_unknown_memory_returns_exit_code_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _persist(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["memory", "show", "memory-" + ("f" * 20)],
    )

    assert result.exit_code == 2


def test_unknown_mission_returns_exit_code_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        memory_cli,
        "_mission_query",
        lambda settings: MissionPlanQuery(MissionPlanStore()),
    )
    monkeypatch.setattr(
        memory_cli,
        "_task_query",
        lambda settings: TaskQuery(TaskStore()),
    )
    monkeypatch.setattr(
        memory_cli,
        "_impact_query",
        lambda settings: ImpactQuery(ImpactDecisionStore()),
    )

    result = runner.invoke(
        app,
        ["memory", "build", "mission-missing"],
    )

    assert result.exit_code == 2


def test_missing_tasks_returns_exit_code_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _ = _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(
        memory_cli,
        "_task_query",
        lambda settings: TaskQuery(TaskStore()),
    )

    result = runner.invoke(
        app,
        ["memory", "build", mission.mission_id],
    )

    assert result.exit_code == 2


def test_missing_impact_returns_exit_code_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, _, _ = _prepare(tmp_path, monkeypatch)
    monkeypatch.setattr(
        memory_cli,
        "_impact_query",
        lambda settings: ImpactQuery(ImpactDecisionStore()),
    )

    result = runner.invoke(
        app,
        ["memory", "build", mission.mission_id],
    )

    assert result.exit_code == 2
