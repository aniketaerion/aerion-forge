"""Task Management CLI integration tests."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from forge.cli import app
from forge.planning.errors import MissionNotFoundError
from forge.planning.models import MissionPlan, MissionWorkstream
from forge.tasks import cli as task_cli
from forge.tasks.errors import TaskNotFoundError
from forge.tasks.query import TaskQuery
from forge.tasks.service import TaskManagementService
from forge.tasks.store import TaskRepository
from tests.test_task_decomposition import _mission

runner = CliRunner()


class MissionQueryStub:
    """Read-only persisted-mission query substitute."""

    def __init__(self, mission: MissionPlan) -> None:
        self.mission = mission

    def get_mission(self, mission_id: str) -> MissionPlan:
        if mission_id != self.mission.mission_id:
            raise MissionNotFoundError(
                f"Mission not found: {mission_id}"
            )

        return self.mission.model_copy(deep=True)


class MissingTaskQueryStub:
    """Task query substitute that always reports a missing task."""

    def get_task(self, task_id: str) -> Any:
        raise TaskNotFoundError(
            f"Task was not found: {task_id}"
        )


def _ready_mission() -> MissionPlan:
    return _mission(
        workstreams=(
            MissionWorkstream(
                workstream_id="workstream-1",
                name="Implement Procurement",
                objective=(
                    "Implement the approved procurement contract."
                ),
                expected_outputs=(
                    "API",
                    "Tests",
                ),
            ),
        )
    )


def _service(tmp_path: Path) -> TaskManagementService:
    return TaskManagementService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )


def test_task_help_contract() -> None:
    task_help = runner.invoke(app, ["task", "--help"])
    build_help = runner.invoke(
        app,
        ["task", "build", "--help"],
    )
    list_help = runner.invoke(
        app,
        ["task", "list", "--help"],
    )
    show_help = runner.invoke(
        app,
        ["task", "show", "--help"],
    )

    assert task_help.exit_code == 0
    assert "build" in task_help.stdout
    assert "list" in task_help.stdout
    assert "show" in task_help.stdout

    assert build_help.exit_code == 0
    assert "--no-persist" in build_help.stdout
    assert "--json" in build_help.stdout

    assert list_help.exit_code == 0
    assert "--mission" in list_help.stdout
    assert "--json" in list_help.stdout

    assert show_help.exit_code == 0
    assert "--json" in show_help.stdout


def test_build_command_uses_persisted_mission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = _ready_mission()
    service = _service(tmp_path)

    monkeypatch.setattr(
        task_cli,
        "_mission_query",
        lambda settings: MissionQueryStub(mission),
    )
    monkeypatch.setattr(
        task_cli,
        "_service",
        lambda settings: service,
    )

    result = runner.invoke(
        app,
        ["task", "build", mission.mission_id],
    )

    assert result.exit_code == 0
    assert mission.mission_id in result.stdout
    assert "Tasks:" in result.stdout
    assert "Reports:" in result.stdout
    assert (
        tmp_path / "memory" / "tasks.json"
    ).is_file()


def test_build_no_persist_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = _ready_mission()
    service = _service(tmp_path)

    monkeypatch.setattr(
        task_cli,
        "_mission_query",
        lambda settings: MissionQueryStub(mission),
    )
    monkeypatch.setattr(
        task_cli,
        "_service",
        lambda settings: service,
    )

    result = runner.invoke(
        app,
        [
            "task",
            "build",
            mission.mission_id,
            "--no-persist",
        ],
    )

    assert result.exit_code == 0
    assert not (
        tmp_path / "memory" / "tasks.json"
    ).exists()
    assert not (tmp_path / "reports").exists()


def test_build_json_is_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = _ready_mission()
    service = _service(tmp_path)

    monkeypatch.setattr(
        task_cli,
        "_mission_query",
        lambda settings: MissionQueryStub(mission),
    )
    monkeypatch.setattr(
        task_cli,
        "_service",
        lambda settings: service,
    )

    first = runner.invoke(
        app,
        [
            "task",
            "build",
            mission.mission_id,
            "--json",
            "--no-persist",
        ],
    )
    second = runner.invoke(
        app,
        [
            "task",
            "build",
            mission.mission_id,
            "--json",
            "--no-persist",
        ],
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert json.loads(first.stdout) == json.loads(second.stdout)


def test_list_and_show_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = _ready_mission()
    service = _service(tmp_path)
    built = service.build(mission)

    repository = TaskRepository(
        tmp_path / "memory" / "tasks.json"
    )
    query = TaskQuery(repository.load())

    monkeypatch.setattr(
        task_cli,
        "_task_query",
        lambda settings: query,
    )

    list_result = runner.invoke(
        app,
        [
            "task",
            "list",
            "--mission",
            mission.mission_id,
        ],
    )

    assert list_result.exit_code == 0
    assert "Engineering Tasks" in list_result.stdout
    assert "Implement" in list_result.stdout
    assert "Procurement" in list_result.stdout

    task_id = built.tasks[0].task_id

    show_result = runner.invoke(
        app,
        ["task", "show", task_id],
    )

    assert show_result.exit_code == 0
    assert task_id in show_result.stdout
    assert "Implement Procurement" in show_result.stdout


def test_list_and_show_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = _ready_mission()
    service = _service(tmp_path)
    built = service.build(mission)

    query = TaskQuery(
        TaskRepository(
            tmp_path / "memory" / "tasks.json"
        ).load()
    )

    monkeypatch.setattr(
        task_cli,
        "_task_query",
        lambda settings: query,
    )

    list_result = runner.invoke(
        app,
        ["task", "list", "--json"],
    )
    show_result = runner.invoke(
        app,
        [
            "task",
            "show",
            built.tasks[0].task_id,
            "--json",
        ],
    )

    assert list_result.exit_code == 0
    assert show_result.exit_code == 0

    listed = json.loads(list_result.stdout)
    shown = json.loads(show_result.stdout)

    assert len(listed) == 3
    assert shown["task_id"] == built.tasks[0].task_id


def test_unknown_mission_returns_exit_code_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission = _ready_mission()

    monkeypatch.setattr(
        task_cli,
        "_mission_query",
        lambda settings: MissionQueryStub(mission),
    )
    monkeypatch.setattr(
        task_cli,
        "_service",
        lambda settings: _service(tmp_path),
    )

    result = runner.invoke(
        app,
        ["task", "build", "mission-missing"],
    )

    assert result.exit_code == 2
    assert "Task build failed" in result.stdout


def test_unknown_task_returns_exit_code_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        task_cli,
        "_task_query",
        lambda settings: MissingTaskQueryStub(),
    )

    result = runner.invoke(
        app,
        ["task", "show", "task-missing"],
    )

    assert result.exit_code == 2
    assert "Task query failed" in result.stdout
