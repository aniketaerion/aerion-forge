"""Mission Reporting validator tests."""

from pathlib import Path

import pytest

from forge.engineering_memory.models import EngineeringMemoryStore
from forge.engineering_memory.service import EngineeringMemoryService
from forge.mission_reporting.errors import (
    MissionReportingDisabledError,
    MissionReportingValidationError,
)
from forge.mission_reporting.models import (
    MissionReportingConfiguration,
    MissionReportingValidationSeverity,
)
from forge.mission_reporting.validator import MissionReportingValidator
from tests.test_engineering_memory_builder import _inputs


def _memory_store(tmp_path: Path) -> EngineeringMemoryStore:
    mission, task_set, assessment = _inputs()
    service = EngineeringMemoryService(
        memory_path=tmp_path / "memory",
        reports_path=tmp_path / "reports",
    )
    service.build(
        mission,
        task_set,
        assessment,
        write_reports=False,
    )
    return service.repository.load()


def test_valid_inputs_pass(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()

    result = MissionReportingValidator().validate(
        mission,
        task_set,
        assessment,
        _memory_store(tmp_path),
    )

    assert result.valid is True
    assert result.messages == ()


def test_disabled_configuration_raises(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    validator = MissionReportingValidator(MissionReportingConfiguration(enabled=False))

    with pytest.raises(MissionReportingDisabledError):
        validator.validate(
            mission,
            task_set,
            assessment,
            _memory_store(tmp_path),
        )


def test_mission_id_mismatch_is_error(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    task_set = task_set.model_copy(update={"mission_id": "mission-other"})

    result = MissionReportingValidator().validate(
        mission,
        task_set,
        assessment,
        _memory_store(tmp_path),
    )

    assert result.valid is False
    assert "mission-id-mismatch" in {item.code for item in result.messages}


def test_mission_fingerprint_mismatch_is_error(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    task_set = task_set.model_copy(update={"mission_fingerprint": "f" * 64})

    result = MissionReportingValidator().validate(
        mission,
        task_set,
        assessment,
        _memory_store(tmp_path),
    )

    assert "mission-fingerprint-mismatch" in {item.code for item in result.messages}


def test_empty_task_set_is_error(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    task_set = task_set.model_copy(update={"tasks": ()})

    result = MissionReportingValidator().validate(
        mission,
        task_set,
        assessment,
        _memory_store(tmp_path),
    )

    assert "empty-task-set" in {item.code for item in result.messages}


def test_assessment_mission_mismatch_is_error(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    assessment = assessment.model_copy(update={"mission_id": "mission-other"})

    result = MissionReportingValidator().validate(
        mission,
        task_set,
        assessment,
        _memory_store(tmp_path),
    )

    assert "assessment-mission-mismatch" in {item.code for item in result.messages}


def test_assessment_task_set_mismatch_is_error(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    assessment = assessment.model_copy(update={"task_set_fingerprint": "f" * 64})

    result = MissionReportingValidator().validate(
        mission,
        task_set,
        assessment,
        _memory_store(tmp_path),
    )

    assert "assessment-task-set-mismatch" in {item.code for item in result.messages}


def test_assessment_task_ids_mismatch_is_error_in_strict_mode(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    assessment = assessment.model_copy(update={"task_ids": ()})

    result = MissionReportingValidator().validate(
        mission,
        task_set,
        assessment,
        _memory_store(tmp_path),
    )

    message = next(
        item for item in result.messages if item.code == "assessment-task-lineage-mismatch"
    )
    assert message.severity is MissionReportingValidationSeverity.ERROR


def test_assessment_task_ids_mismatch_is_warning_in_non_strict_mode(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    assessment = assessment.model_copy(update={"task_ids": ()})
    validator = MissionReportingValidator(MissionReportingConfiguration(strict=False))

    result = validator.validate(
        mission,
        task_set,
        assessment,
        _memory_store(tmp_path),
    )

    message = next(
        item for item in result.messages if item.code == "assessment-task-lineage-mismatch"
    )
    assert message.severity is MissionReportingValidationSeverity.WARNING
    assert result.valid is True


def test_missing_memory_generation_is_error() -> None:
    mission, task_set, assessment = _inputs()

    result = MissionReportingValidator().validate(
        mission,
        task_set,
        assessment,
        EngineeringMemoryStore(),
    )

    assert "missing-memory-generation" in {item.code for item in result.messages}


def test_empty_memory_records_is_error(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    store = _memory_store(tmp_path).model_copy(update={"records": {}})

    result = MissionReportingValidator().validate(
        mission,
        task_set,
        assessment,
        store,
    )

    assert "empty-engineering-memory" in {item.code for item in result.messages}


def test_missing_mission_lineage_is_error_in_strict_mode(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    store = _memory_store(tmp_path)
    records = {
        key: record.model_copy(update={"mission_ids": ()}) for key, record in store.records.items()
    }
    store = store.model_copy(update={"records": records})

    result = MissionReportingValidator().validate(
        mission,
        task_set,
        assessment,
        store,
    )

    assert "missing-mission-memory" in {item.code for item in result.messages}


def test_missing_assessment_lineage_is_warning_in_non_strict_mode(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    store = _memory_store(tmp_path)
    records = {
        key: record.model_copy(update={"assessment_ids": ()})
        for key, record in store.records.items()
    }
    store = store.model_copy(update={"records": records})
    validator = MissionReportingValidator(MissionReportingConfiguration(strict=False))

    result = validator.validate(
        mission,
        task_set,
        assessment,
        store,
    )

    message = next(item for item in result.messages if item.code == "missing-assessment-memory")
    assert message.severity is MissionReportingValidationSeverity.WARNING
    assert result.valid is True


def test_validate_or_raise_returns_valid_result(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()

    result = MissionReportingValidator().validate_or_raise(
        mission,
        task_set,
        assessment,
        _memory_store(tmp_path),
    )

    assert result.valid is True


def test_validate_or_raise_raises_for_errors(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    task_set = task_set.model_copy(update={"mission_id": "mission-other"})

    with pytest.raises(MissionReportingValidationError):
        MissionReportingValidator().validate_or_raise(
            mission,
            task_set,
            assessment,
            _memory_store(tmp_path),
        )
