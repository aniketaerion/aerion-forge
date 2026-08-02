"""Mission Reporting model tests."""

from types import MappingProxyType

import pytest
from pydantic import ValidationError

from forge.mission_reporting.models import (
    MissionReport,
    MissionReportingConfiguration,
    MissionReportingResult,
    MissionReportingValidationMessage,
    MissionReportingValidationResult,
    MissionReportingValidationSeverity,
    MissionReportRisk,
    MissionReportRiskSeverity,
    MissionReportSection,
    MissionReportSectionType,
    MissionReportStatistics,
    MissionReportStatus,
    MissionTraceabilityItem,
)


def _section() -> MissionReportSection:
    return MissionReportSection(
        section_id="mission-section-001",
        section_type=MissionReportSectionType.MISSION,
        title=" Mission ",
        summary=" Mission summary ",
        content=(" First ", "", "Second"),
        source_ids=("mission-001",),
    )


def _risk() -> MissionReportRisk:
    return MissionReportRisk(
        risk_id="mission-risk-001",
        title=" Delivery risk ",
        description=" Delivery may be delayed. ",
        severity=MissionReportRiskSeverity.HIGH,
        source_type="impact-finding",
        source_id="finding-001",
        affected_task_ids=("task-002", "task-001", "task-001", ""),
        mitigation="Validate dependencies.",
    )


def _traceability() -> MissionTraceabilityItem:
    return MissionTraceabilityItem(
        traceability_id="mission-trace-001",
        source_type="mission",
        source_id="mission-001",
        target_type="task",
        target_id="task-001",
        relationship="decomposes-to",
        evidence_ids=("evidence-002", "evidence-001", "evidence-001", ""),
    )


def _statistics() -> MissionReportStatistics:
    return MissionReportStatistics(
        task_count=2,
        blocked_task_count=0,
        risk_count=1,
        high_risk_count=1,
        critical_risk_count=0,
        traceability_count=1,
        section_count=1,
        engineering_memory_record_count=3,
    )


def _report() -> MissionReport:
    return MissionReport(
        report_id="mission-report-001",
        mission_id="mission-001",
        mission_fingerprint="a" * 64,
        task_set_fingerprint="b" * 64,
        assessment_id="impact-001",
        assessment_fingerprint="c" * 64,
        engineering_memory_generation_id="memory-generation-001",
        title=" Mission Report ",
        executive_summary=" Mission is ready. ",
        status=MissionReportStatus.READY,
        sections=(_section(),),
        risks=(_risk(),),
        traceability=(_traceability(),),
        statistics=_statistics(),
        source_fingerprints={
            "task_set": "b" * 64,
            "mission": "a" * 64,
        },
        report_fingerprint="d" * 64,
    )


def test_section_normalizes_required_text() -> None:
    section = _section()

    assert section.title == "Mission"
    assert section.summary == "Mission summary"


def test_section_removes_blank_content() -> None:
    section = _section()

    assert section.content == ("First", "Second")


def test_risk_normalizes_and_sorts_task_ids() -> None:
    risk = _risk()

    assert risk.affected_task_ids == ("task-001", "task-002")


def test_traceability_normalizes_evidence_ids() -> None:
    item = _traceability()

    assert item.evidence_ids == ("evidence-001", "evidence-002")


def test_statistics_reject_blocked_count_above_total() -> None:
    with pytest.raises(ValidationError):
        MissionReportStatistics(
            task_count=1,
            blocked_task_count=2,
            risk_count=0,
            high_risk_count=0,
            critical_risk_count=0,
            traceability_count=0,
            section_count=0,
            engineering_memory_record_count=0,
        )


def test_statistics_reject_high_risk_count_above_total() -> None:
    with pytest.raises(ValidationError):
        MissionReportStatistics(
            task_count=0,
            blocked_task_count=0,
            risk_count=1,
            high_risk_count=2,
            critical_risk_count=0,
            traceability_count=0,
            section_count=0,
            engineering_memory_record_count=0,
        )


def test_report_normalizes_source_fingerprints() -> None:
    report = _report()

    assert list(report.source_fingerprints) == ["mission", "task_set"]
    assert isinstance(report.source_fingerprints, MappingProxyType)


def test_report_rejects_section_count_mismatch() -> None:
    with pytest.raises(ValidationError):
        _report().model_copy(
            update={"statistics": _statistics().model_copy(update={"section_count": 2})}
        ).model_validate(
            _report()
            .model_copy(
                update={"statistics": _statistics().model_copy(update={"section_count": 2})}
            )
            .model_dump()
        )


def test_report_rejects_risk_count_mismatch() -> None:
    payload = _report().model_dump()
    payload["statistics"]["risk_count"] = 0

    with pytest.raises(ValidationError):
        MissionReport.model_validate(payload)


def test_report_rejects_traceability_count_mismatch() -> None:
    payload = _report().model_dump()
    payload["statistics"]["traceability_count"] = 0

    with pytest.raises(ValidationError):
        MissionReport.model_validate(payload)


def test_configuration_defaults_are_enabled_and_strict() -> None:
    configuration = MissionReportingConfiguration()

    assert configuration.enabled is True
    assert configuration.strict is True
    assert configuration.include_engineering_memory is True


def test_configuration_rejects_invalid_limits() -> None:
    with pytest.raises(ValidationError):
        MissionReportingConfiguration(max_sections=0)


def test_validation_result_accepts_valid_without_errors() -> None:
    result = MissionReportingValidationResult(
        valid=True,
        messages=(
            MissionReportingValidationMessage(
                severity=MissionReportingValidationSeverity.WARNING,
                code="warning",
                message="Warning only.",
            ),
        ),
    )

    assert result.valid is True


def test_validation_result_rejects_valid_with_error() -> None:
    with pytest.raises(ValidationError):
        MissionReportingValidationResult(
            valid=True,
            messages=(
                MissionReportingValidationMessage(
                    severity=MissionReportingValidationSeverity.ERROR,
                    code="error",
                    message="Invalid.",
                ),
            ),
        )


def test_result_wraps_report_and_paths() -> None:
    result = MissionReportingResult(
        report=_report(),
        report_paths=("MISSION_REPORT.json",),
    )

    assert result.report.report_id == "mission-report-001"
    assert result.report_paths == ("MISSION_REPORT.json",)
