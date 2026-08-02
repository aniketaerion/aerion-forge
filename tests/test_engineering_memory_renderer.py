"""Engineering Memory renderer tests."""

import json
from pathlib import Path

import pytest

from forge.engineering_memory.builder import (
    EngineeringMemoryBuilder,
)
from forge.engineering_memory.errors import (
    EngineeringMemoryReportError,
)
from forge.engineering_memory.identifiers import (
    build_generation_id,
    build_store_fingerprint,
)
from forge.engineering_memory.models import (
    EngineeringMemoryGeneration,
    EngineeringMemoryStatistics,
    MemoryRecord,
    MemoryRetentionPolicy,
)
from forge.engineering_memory.renderer import (
    EngineeringMemoryRenderer,
)
from tests.test_engineering_memory_builder import _inputs


def _records() -> tuple[MemoryRecord, ...]:
    mission, task_set, assessment = _inputs()

    return EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )


def _generation(
    records: tuple[MemoryRecord, ...],
) -> EngineeringMemoryGeneration:
    active = {record.memory_id: record for record in records}
    fingerprint = build_store_fingerprint(active)

    return EngineeringMemoryGeneration(
        generation_id=build_generation_id(
            store_fingerprint=fingerprint,
        ),
        store_fingerprint=fingerprint,
        record_count=len(records),
        relationship_count=sum(len(record.relationships) for record in records),
        evidence_count=sum(len(record.evidence) for record in records),
    )


def _statistics(
    records: tuple[MemoryRecord, ...],
) -> EngineeringMemoryStatistics:
    return EngineeringMemoryStatistics(
        record_count=len(records),
        relationship_count=sum(len(record.relationships) for record in records),
        evidence_count=sum(len(record.evidence) for record in records),
        mission_count=len({mission_id for record in records for mission_id in record.mission_ids}),
        task_count=len({task_id for record in records for task_id in record.task_ids}),
        assessment_count=len(
            {assessment_id for record in records for assessment_id in record.assessment_ids}
        ),
        capability_count=len(
            {capability_id for record in records for capability_id in record.capability_ids}
        ),
        permanent_record_count=sum(
            record.retention_policy is MemoryRetentionPolicy.PERMANENT for record in records
        ),
    )


def _reports() -> dict[str, str]:
    records = _records()

    return EngineeringMemoryRenderer().render(
        records,
        _generation(records),
        _statistics(records),
    )


def test_render_returns_complete_report_suite() -> None:
    reports = _reports()

    assert set(reports) == set(EngineeringMemoryRenderer.REPORT_NAMES)


def test_render_is_deterministic() -> None:
    records = _records()
    renderer = EngineeringMemoryRenderer()
    generation = _generation(records)
    statistics = _statistics(records)

    first = renderer.render(
        records,
        generation,
        statistics,
    )
    second = renderer.render(
        tuple(reversed(records)),
        generation,
        statistics,
    )

    assert first == second


def test_memory_json_is_valid() -> None:
    reports = _reports()

    payload = json.loads(reports["ENGINEERING_MEMORY.json"])

    assert payload["schema_version"] == "1.0"
    assert len(payload["records"]) == 3


def test_summary_json_is_valid() -> None:
    reports = _reports()

    payload = json.loads(reports["ENGINEERING_MEMORY_SUMMARY.json"])

    assert payload["record_count"] == 3
    assert payload["relationship_count"] == 2
    assert payload["evidence_count"] == 3


def test_summary_contains_memory_type_counts() -> None:
    payload = json.loads(_reports()["ENGINEERING_MEMORY_SUMMARY.json"])

    assert payload["memory_types"] == {
        "decision": 1,
        "mission": 1,
        "task": 1,
    }


def test_lineage_json_is_valid() -> None:
    payload = json.loads(_reports()["ENGINEERING_MEMORY_LINEAGE.json"])

    assert len(payload["records"]) == 3
    assert all("relationships" in record for record in payload["records"])


def test_markdown_contains_generation() -> None:
    records = _records()
    generation = _generation(records)

    markdown = EngineeringMemoryRenderer().render(
        records,
        generation,
        _statistics(records),
    )["ENGINEERING_MEMORY.md"]

    assert generation.generation_id in markdown


def test_markdown_contains_all_records() -> None:
    records = _records()

    markdown = EngineeringMemoryRenderer().render(
        records,
        _generation(records),
        _statistics(records),
    )["ENGINEERING_MEMORY.md"]

    for record in records:
        assert record.memory_id in markdown
        assert record.title in markdown


def test_markdown_contains_safety_boundary() -> None:
    markdown = _reports()["ENGINEERING_MEMORY.md"]

    assert "## Safety Boundary" in markdown
    assert "does not execute tasks" in markdown


def test_write_creates_all_reports(
    tmp_path: Path,
) -> None:
    renderer = EngineeringMemoryRenderer()

    paths = renderer.write(
        tmp_path,
        _reports(),
    )

    assert len(paths) == 4

    for report_name in renderer.REPORT_NAMES:
        assert (tmp_path / report_name).is_file()


def test_written_reports_match_rendered_content(
    tmp_path: Path,
) -> None:
    renderer = EngineeringMemoryRenderer()
    reports = _reports()

    renderer.write(
        tmp_path,
        reports,
    )

    for report_name, content in reports.items():
        assert (tmp_path / report_name).read_text(encoding="utf-8") == content


def test_write_rejects_missing_report(
    tmp_path: Path,
) -> None:
    reports = _reports()
    reports.pop("ENGINEERING_MEMORY.md")

    with pytest.raises(EngineeringMemoryReportError):
        EngineeringMemoryRenderer().write(
            tmp_path,
            reports,
        )


def test_write_rejects_extra_report(
    tmp_path: Path,
) -> None:
    reports = _reports()
    reports["EXTRA.txt"] = "invalid"

    with pytest.raises(EngineeringMemoryReportError):
        EngineeringMemoryRenderer().write(
            tmp_path,
            reports,
        )


def test_write_returns_paths_in_frozen_order(
    tmp_path: Path,
) -> None:
    renderer = EngineeringMemoryRenderer()

    paths = renderer.write(
        tmp_path,
        _reports(),
    )

    assert tuple(Path(path).name for path in paths) == renderer.REPORT_NAMES


def test_write_overwrites_existing_reports(
    tmp_path: Path,
) -> None:
    renderer = EngineeringMemoryRenderer()

    for name in renderer.REPORT_NAMES:
        (tmp_path / name).write_text(
            "old",
            encoding="utf-8",
        )

    reports = _reports()
    renderer.write(
        tmp_path,
        reports,
    )

    for name in renderer.REPORT_NAMES:
        assert (tmp_path / name).read_text(encoding="utf-8") == reports[name]


def test_atomic_write_failure_raises_report_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    renderer = EngineeringMemoryRenderer()

    def fail(
        path: Path,
        content: bytes,
    ) -> None:
        raise EngineeringMemoryReportError("forced failure")

    monkeypatch.setattr(
        renderer,
        "_atomic_write",
        fail,
    )

    with pytest.raises(EngineeringMemoryReportError):
        renderer.write(
            tmp_path,
            _reports(),
        )


def test_failed_write_restores_existing_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    renderer = EngineeringMemoryRenderer()

    originals = {name: f"original-{name}" for name in renderer.REPORT_NAMES}

    for name, content in originals.items():
        (tmp_path / name).write_text(
            content,
            encoding="utf-8",
        )

    real_atomic_write = renderer._atomic_write
    call_count = 0

    def fail_second(
        path: Path,
        content: bytes,
    ) -> None:
        nonlocal call_count
        call_count += 1

        if call_count == 2:
            raise EngineeringMemoryReportError("forced failure")

        real_atomic_write(
            path,
            content,
        )

    monkeypatch.setattr(
        renderer,
        "_atomic_write",
        fail_second,
    )

    with pytest.raises(EngineeringMemoryReportError):
        renderer.write(
            tmp_path,
            _reports(),
        )

    for name, content in originals.items():
        assert (tmp_path / name).read_text(encoding="utf-8") == content
