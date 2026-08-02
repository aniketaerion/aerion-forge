"""Task Management service tests."""

from pathlib import Path

import pytest

from forge.planning.models import MissionPlan, MissionWorkstream
from forge.tasks.errors import (
    TaskManagementDisabledError,
    TaskReportError,
)
from forge.tasks.models import (
    TaskChangeType,
    TaskManagementConfiguration,
)
from forge.tasks.renderer import TaskRenderer
from forge.tasks.service import TaskManagementService
from tests.test_task_decomposition import _mission


class FailingRenderer(TaskRenderer):
    """Renderer that simulates a report failure."""

    def write(
        self,
        directory: Path,
        reports: dict[str, str],
    ) -> tuple[str, ...]:
        raise TaskReportError(
            "Simulated task report failure."
        )


def _ready_mission() -> MissionPlan:
    return _mission(
        workstreams=(
            MissionWorkstream(
                workstream_id="workstream-1",
                name="Implement Procurement",
                objective="Implement the approved procurement contract.",
                expected_outputs=(
                    "API",
                    "Tests",
                ),
            ),
        )
    )


def test_service_builds_persists_and_reports(
    tmp_path: Path,
) -> None:
    service = TaskManagementService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )

    result = service.build(_ready_mission())

    assert len(result.tasks) == 3
    assert result.generation.task_count == 3
    assert all(
        change.change_type is TaskChangeType.CREATED
        for change in result.changes.changes
    )
    assert (
        tmp_path / "memory" / "tasks.json"
    ).is_file()
    assert len(result.report_paths) == 5


def test_repeated_build_is_unchanged(
    tmp_path: Path,
) -> None:
    service = TaskManagementService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )
    mission = _ready_mission()

    first = service.build(mission)
    second = service.build(mission)

    assert (
        first.generation.generation_id
        == second.generation.generation_id
    )
    assert all(
        change.change_type is TaskChangeType.UNCHANGED
        for change in second.changes.changes
    )


def test_no_persist_writes_no_store(
    tmp_path: Path,
) -> None:
    service = TaskManagementService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )

    service.build(
        _ready_mission(),
        persist=False,
        write_reports=False,
    )

    assert not (
        tmp_path / "memory" / "tasks.json"
    ).exists()
    assert not (tmp_path / "reports").exists()


def test_disabled_service_is_rejected(
    tmp_path: Path,
) -> None:
    service = TaskManagementService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
        configuration=TaskManagementConfiguration(
            enabled=False
        ),
    )

    with pytest.raises(TaskManagementDisabledError):
        service.build(_ready_mission())


def test_report_failure_rolls_back_store(
    tmp_path: Path,
) -> None:
    memory = tmp_path / "memory"
    reports = tmp_path / "reports"

    service = TaskManagementService(
        memory_path=memory,
        reports_path=reports,
    )
    service.build(_ready_mission())

    store_before = (
        memory / "tasks.json"
    ).read_bytes()
    report_before = {
        path.name: path.read_bytes()
        for path in reports.iterdir()
    }

    failing = TaskManagementService(
        memory_path=memory,
        reports_path=reports,
        renderer=FailingRenderer(),
    )

    with pytest.raises(TaskReportError):
        failing.build(_ready_mission())

    assert (
        memory / "tasks.json"
    ).read_bytes() == store_before

    assert {
        path.name: path.read_bytes()
        for path in reports.iterdir()
    } == report_before


def test_reports_can_be_disabled(
    tmp_path: Path,
) -> None:
    service = TaskManagementService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )

    result = service.build(
        _ready_mission(),
        write_reports=False,
    )

    assert result.report_paths == ()
    assert (
        tmp_path / "memory" / "tasks.json"
    ).is_file()
    assert not (tmp_path / "reports").exists()
