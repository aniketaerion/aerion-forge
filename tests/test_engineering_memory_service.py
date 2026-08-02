"""Engineering Memory service tests."""

from pathlib import Path

import pytest

from forge.engineering_memory.errors import (
    EngineeringMemoryDisabledError,
    EngineeringMemoryReportError,
)
from forge.engineering_memory.models import (
    EngineeringMemoryConfiguration,
)
from forge.engineering_memory.query import (
    EngineeringMemoryQuery,
)
from forge.engineering_memory.renderer import (
    EngineeringMemoryRenderer,
)
from forge.engineering_memory.service import (
    EngineeringMemoryService,
)
from forge.engineering_memory.store import (
    EngineeringMemoryRepository,
)
from tests.test_engineering_memory_builder import _inputs


def _service(
    tmp_path: Path,
    *,
    configuration: (EngineeringMemoryConfiguration | None) = None,
    renderer: EngineeringMemoryRenderer | None = None,
) -> EngineeringMemoryService:
    return EngineeringMemoryService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
        configuration=configuration,
        renderer=renderer,
    )


def test_build_returns_three_records(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()

    result = _service(tmp_path).build(
        mission,
        task_set,
        assessment,
    )

    assert len(result.records) == 3


def test_build_persists_store(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    service = _service(tmp_path)

    service.build(
        mission,
        task_set,
        assessment,
    )

    store = EngineeringMemoryRepository(tmp_path / "memory" / "engineering-memory.json").load()

    assert len(store.records) == 3


def test_build_writes_reports(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()

    result = _service(tmp_path).build(
        mission,
        task_set,
        assessment,
    )

    assert len(result.report_paths) == 4

    for path in result.report_paths:
        assert Path(path).is_file()


def test_build_can_skip_persistence(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()

    _service(tmp_path).build(
        mission,
        task_set,
        assessment,
        persist=False,
    )

    assert not (tmp_path / "memory" / "engineering-memory.json").exists()


def test_build_can_skip_reports(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()

    result = _service(tmp_path).build(
        mission,
        task_set,
        assessment,
        write_reports=False,
    )

    assert result.report_paths == ()
    assert not (tmp_path / "reports").exists()


def test_build_can_skip_persistence_and_reports(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()

    result = _service(tmp_path).build(
        mission,
        task_set,
        assessment,
        persist=False,
        write_reports=False,
    )

    assert len(result.records) == 3
    assert result.report_paths == ()
    assert not (tmp_path / "memory").exists()
    assert not (tmp_path / "reports").exists()


def test_disabled_configuration_is_rejected(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    configuration = EngineeringMemoryConfiguration(enabled=False)

    with pytest.raises(EngineeringMemoryDisabledError):
        _service(
            tmp_path,
            configuration=configuration,
        ).build(
            mission,
            task_set,
            assessment,
        )


def test_statistics_are_correct(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()

    result = _service(tmp_path).build(
        mission,
        task_set,
        assessment,
        persist=False,
        write_reports=False,
    )

    assert result.statistics.record_count == 3
    assert result.statistics.relationship_count == 2
    assert result.statistics.evidence_count == 3
    assert result.statistics.mission_count == 1
    assert result.statistics.task_count == len(task_set.tasks)
    assert result.statistics.assessment_count == 1
    assert result.statistics.capability_count == 3
    assert result.statistics.permanent_record_count == 1


def test_generation_matches_records(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()

    result = _service(tmp_path).build(
        mission,
        task_set,
        assessment,
        persist=False,
        write_reports=False,
    )

    assert result.generation.record_count == len(result.records)
    assert result.generation.relationship_count == result.statistics.relationship_count
    assert result.generation.evidence_count == result.statistics.evidence_count


def test_repeated_build_links_generation(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    service = _service(tmp_path)

    first = service.build(
        mission,
        task_set,
        assessment,
        write_reports=False,
    )
    second = service.build(
        mission,
        task_set,
        assessment,
        write_reports=False,
    )

    assert second.generation.previous_generation_id == first.generation.generation_id


def test_result_records_are_sorted(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()

    result = _service(tmp_path).build(
        mission,
        task_set,
        assessment,
        persist=False,
        write_reports=False,
    )

    assert tuple(record.memory_id for record in result.records) == tuple(
        sorted(record.memory_id for record in result.records)
    )


def test_persisted_records_are_queryable(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    service = _service(tmp_path)

    service.build(
        mission,
        task_set,
        assessment,
        write_reports=False,
    )

    store = service.repository.load()
    query = EngineeringMemoryQuery(store)

    assert len(query.by_mission(mission.mission_id)) == 3


def test_report_failure_restores_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, task_set, assessment = _inputs()
    renderer = EngineeringMemoryRenderer()
    service = _service(
        tmp_path,
        renderer=renderer,
    )

    service.build(
        mission,
        task_set,
        assessment,
        write_reports=False,
    )

    store_path = tmp_path / "memory" / "engineering-memory.json"
    original = store_path.read_bytes()

    def fail_write(
        directory: Path,
        reports: dict[str, str],
    ) -> tuple[str, ...]:
        raise EngineeringMemoryReportError("forced report failure")

    monkeypatch.setattr(
        renderer,
        "write",
        fail_write,
    )

    with pytest.raises(EngineeringMemoryReportError):
        service.build(
            mission,
            task_set,
            assessment,
        )

    assert store_path.read_bytes() == original

    restored = service.repository.load()

    assert len(restored.records) == 3
    assert restored.generation is not None


def test_report_failure_restores_existing_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mission, task_set, assessment = _inputs()
    renderer = EngineeringMemoryRenderer()
    service = _service(
        tmp_path,
        renderer=renderer,
    )

    reports_path = tmp_path / "reports"
    reports_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    originals = {name: f"original-{name}".encode() for name in renderer.REPORT_NAMES}

    for name, content in originals.items():
        (reports_path / name).write_bytes(content)

    def fail_write(
        directory: Path,
        reports: dict[str, str],
    ) -> tuple[str, ...]:
        raise EngineeringMemoryReportError("forced report failure")

    monkeypatch.setattr(
        renderer,
        "write",
        fail_write,
    )

    with pytest.raises(EngineeringMemoryReportError):
        service.build(
            mission,
            task_set,
            assessment,
        )

    for name, content in originals.items():
        assert (reports_path / name).read_bytes() == content


def test_service_uses_configured_history_limit(
    tmp_path: Path,
) -> None:
    configuration = EngineeringMemoryConfiguration(history_limit=9)
    service = _service(
        tmp_path,
        configuration=configuration,
    )

    assert service.repository.history_limit == 9


def test_service_store_name_is_frozen() -> None:
    assert EngineeringMemoryService.STORE_NAME == "engineering-memory.json"
