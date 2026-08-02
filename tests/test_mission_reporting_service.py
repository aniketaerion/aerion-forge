"""Mission Reporting service tests."""

from collections.abc import Mapping
from pathlib import Path

import pytest

from forge.mission_reporting.builder import MissionReportBuilder
from forge.mission_reporting.errors import (
    MissionReportingDisabledError,
    MissionReportingReportError,
)
from forge.mission_reporting.models import (
    MissionReport,
    MissionReportingConfiguration,
    MissionReportingResult,
)
from forge.mission_reporting.renderer import (
    REPORT_NAMES,
    MissionReportRenderer,
)
from forge.mission_reporting.service import (
    MissionReportingService,
)
from tests.test_engineering_memory_builder import _inputs
from tests.test_mission_reporting_validation import _memory_store


def _service(
    tmp_path: Path,
    configuration: MissionReportingConfiguration | None = None,
    *,
    builder: MissionReportBuilder | None = None,
    renderer: MissionReportRenderer | None = None,
) -> MissionReportingService:
    return MissionReportingService(
        reports_path=tmp_path / "reports",
        configuration=configuration,
        builder=builder,
        renderer=renderer,
    )


def _build(
    tmp_path: Path,
    *,
    write_reports: bool = True,
) -> MissionReportingResult:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    return _service(tmp_path).build(
        mission,
        task_set,
        assessment,
        memory,
        write_reports=write_reports,
    )


def test_service_build_returns_report(
    tmp_path: Path,
) -> None:
    result = _build(
        tmp_path,
        write_reports=False,
    )

    assert isinstance(result.report, MissionReport)
    assert result.report.report_id


def test_service_writes_complete_report_suite(
    tmp_path: Path,
) -> None:
    result = _build(tmp_path)

    assert len(result.report_paths) == len(REPORT_NAMES)

    assert tuple(Path(path).name for path in result.report_paths) == REPORT_NAMES


def test_service_report_paths_exist(
    tmp_path: Path,
) -> None:
    result = _build(tmp_path)

    for path in result.report_paths:
        assert Path(path).is_file()


def test_service_can_skip_report_writes(
    tmp_path: Path,
) -> None:
    result = _build(
        tmp_path,
        write_reports=False,
    )

    assert result.report_paths == ()
    assert not (tmp_path / "reports").exists()


def test_service_result_matches_written_json(
    tmp_path: Path,
) -> None:
    result = _build(tmp_path)

    report_path = tmp_path / "reports" / "MISSION_REPORT.json"

    assert report_path.is_file()
    assert result.report.report_id in report_path.read_text(encoding="utf-8")


def test_service_is_deterministic_for_fixed_inputs(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)
    service = _service(tmp_path)

    first = service.build(
        mission,
        task_set,
        assessment,
        memory,
        write_reports=False,
    )
    second = service.build(
        mission,
        task_set,
        assessment,
        memory,
        write_reports=False,
    )

    assert first.report == second.report
    assert first.report.report_fingerprint == second.report.report_fingerprint


def test_service_overwrites_existing_reports(
    tmp_path: Path,
) -> None:
    reports_path = tmp_path / "reports"
    reports_path.mkdir()

    for name in REPORT_NAMES:
        (reports_path / name).write_bytes(b"old")

    result = _build(tmp_path)

    for path in result.report_paths:
        assert Path(path).read_bytes() != b"old"


def test_service_rejects_disabled_configuration(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    service = _service(
        tmp_path,
        MissionReportingConfiguration(
            enabled=False,
        ),
    )

    with pytest.raises(MissionReportingDisabledError):
        service.build(
            mission,
            task_set,
            assessment,
            memory,
        )


def test_service_propagates_renderer_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)
    renderer = MissionReportRenderer()
    service = _service(
        tmp_path,
        renderer=renderer,
    )

    def fail_write(
        directory: Path,
        rendered: object,
    ) -> tuple[Path, ...]:
        raise MissionReportingReportError("simulated renderer failure")

    monkeypatch.setattr(
        renderer,
        "write",
        fail_write,
    )

    with pytest.raises(MissionReportingReportError):
        service.build(
            mission,
            task_set,
            assessment,
            memory,
        )


def test_renderer_failure_does_not_return_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)
    renderer = MissionReportRenderer()
    service = _service(
        tmp_path,
        renderer=renderer,
    )

    def fail_render(
        report: MissionReport,
    ) -> dict[str, bytes]:
        raise MissionReportingReportError("simulated render failure")

    monkeypatch.setattr(
        renderer,
        "render",
        fail_render,
    )

    with pytest.raises(MissionReportingReportError):
        service.build(
            mission,
            task_set,
            assessment,
            memory,
        )


def test_service_uses_injected_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)
    builder = MissionReportBuilder()
    expected = builder.build(
        mission,
        task_set,
        assessment,
        memory,
    )
    called = False

    def build_report(
        mission_value: object,
        task_set_value: object,
        assessment_value: object,
        memory_value: object,
    ) -> MissionReport:
        nonlocal called
        called = True
        return expected

    monkeypatch.setattr(
        builder,
        "build",
        build_report,
    )

    result = _service(
        tmp_path,
        builder=builder,
    ).build(
        mission,
        task_set,
        assessment,
        memory,
        write_reports=False,
    )

    assert called is True
    assert result.report == expected


def test_service_uses_injected_renderer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)
    renderer = MissionReportRenderer()
    called = False
    original_render = renderer.render

    def render_report(
        report: MissionReport,
    ) -> Mapping[str, bytes]:
        nonlocal called
        called = True
        return original_render(report)

    monkeypatch.setattr(
        renderer,
        "render",
        render_report,
    )

    _service(
        tmp_path,
        renderer=renderer,
    ).build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert called is True


def test_service_preserves_report_lineage(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    result = _service(tmp_path).build(
        mission,
        task_set,
        assessment,
        memory,
        write_reports=False,
    )

    assert result.report.mission_id == mission.mission_id
    assert result.report.task_set_fingerprint == task_set.task_set_fingerprint
    assert result.report.assessment_id == assessment.assessment_id


def test_service_reports_path_is_configured(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)

    assert service.reports_path == tmp_path / "reports"


def test_service_default_configuration_is_enabled(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)

    assert service.configuration.enabled is True


def test_service_does_not_modify_engineering_memory(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)
    before = memory.model_dump(mode="json")

    _service(tmp_path).build(
        mission,
        task_set,
        assessment,
        memory,
        write_reports=False,
    )

    assert memory.model_dump(mode="json") == before
