"""Impact Decision service tests."""

from pathlib import Path

import pytest

from forge.impact.errors import (
    ImpactDecisionDisabledError,
    ImpactReportError,
)
from forge.impact.models import (
    ImpactDecisionConfiguration,
)
from forge.impact.renderer import ImpactRenderer
from forge.impact.service import ImpactDecisionService
from forge.planning.models import (
    MissionPlan,
    MissionWorkstream,
)
from forge.tasks.decomposer import decompose_mission
from forge.tasks.models import TaskSet
from tests.test_task_decomposition import _mission


class FailingRenderer(ImpactRenderer):
    """Renderer that simulates report-write failure."""

    def write(
        self,
        directory: Path,
        reports: dict[str, str],
    ) -> tuple[str, ...]:
        raise ImpactReportError("Simulated impact report failure.")


def _inputs() -> tuple[MissionPlan, TaskSet]:
    mission = _mission(
        workstreams=(
            MissionWorkstream(
                workstream_id="workstream-service",
                name="Build Service",
                objective="Build the Impact Decision service.",
                expected_outputs=("Service",),
            ),
        )
    )
    return mission, decompose_mission(mission)


def test_service_builds_persists_and_reports(
    tmp_path: Path,
) -> None:
    mission, task_set = _inputs()
    service = ImpactDecisionService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )

    result = service.assess(mission, task_set)

    assert result.assessment.mission_id == mission.mission_id
    assert (tmp_path / "memory" / "impact-decisions.json").is_file()
    assert len(result.report_paths) == 4


def test_repeated_assessment_is_deterministic(
    tmp_path: Path,
) -> None:
    mission, task_set = _inputs()
    service = ImpactDecisionService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )

    first = service.assess(mission, task_set)
    second = service.assess(mission, task_set)

    assert first.assessment == second.assessment
    assert second.generation.previous_generation_id == first.generation.generation_id


def test_no_persist_writes_no_store(
    tmp_path: Path,
) -> None:
    mission, task_set = _inputs()
    service = ImpactDecisionService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )

    service.assess(
        mission,
        task_set,
        persist=False,
        write_reports=False,
    )

    assert not (tmp_path / "memory" / "impact-decisions.json").exists()
    assert not (tmp_path / "reports").exists()


def test_disabled_service_is_rejected(
    tmp_path: Path,
) -> None:
    mission, task_set = _inputs()
    service = ImpactDecisionService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
        configuration=ImpactDecisionConfiguration(enabled=False),
    )

    with pytest.raises(ImpactDecisionDisabledError):
        service.assess(mission, task_set)


def test_report_failure_rolls_back_store(
    tmp_path: Path,
) -> None:
    mission, task_set = _inputs()
    memory = tmp_path / "memory"
    reports = tmp_path / "reports"

    service = ImpactDecisionService(
        memory_path=memory,
        reports_path=reports,
    )
    service.assess(mission, task_set)

    store_before = (memory / "impact-decisions.json").read_bytes()
    reports_before = {path.name: path.read_bytes() for path in reports.iterdir()}

    failing = ImpactDecisionService(
        memory_path=memory,
        reports_path=reports,
        renderer=FailingRenderer(),
    )

    with pytest.raises(ImpactReportError):
        failing.assess(mission, task_set)

    assert (memory / "impact-decisions.json").read_bytes() == store_before

    assert {path.name: path.read_bytes() for path in reports.iterdir()} == reports_before


def test_reports_can_be_disabled(
    tmp_path: Path,
) -> None:
    mission, task_set = _inputs()
    service = ImpactDecisionService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )

    result = service.assess(
        mission,
        task_set,
        write_reports=False,
    )

    assert result.report_paths == ()
    assert (tmp_path / "memory" / "impact-decisions.json").is_file()
    assert not (tmp_path / "reports").exists()
