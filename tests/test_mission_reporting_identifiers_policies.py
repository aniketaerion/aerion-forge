"""Mission Reporting identifier and policy tests."""

from forge.impact.models import DecisionStatus, ImpactSeverity
from forge.mission_reporting.identifiers import (
    build_report_fingerprint,
    build_report_id,
    build_risk_fingerprint,
    build_risk_id,
    build_section_fingerprint,
    build_section_id,
    build_traceability_fingerprint,
    build_traceability_id,
)
from forge.mission_reporting.models import (
    MissionReportRiskSeverity,
    MissionReportSectionType,
    MissionReportStatus,
)
from forge.mission_reporting.policies import (
    derive_report_status,
    map_risk_severity,
    required_section_types,
    section_sort_key,
    should_include_risk,
)
from tests.test_engineering_memory_builder import _inputs
from tests.test_mission_reporting_models import (
    _report,
    _risk,
    _section,
    _traceability,
)


def test_report_id_is_deterministic() -> None:
    kwargs = {
        "mission_id": "mission-001",
        "mission_fingerprint": "a" * 64,
        "task_set_fingerprint": "b" * 64,
        "assessment_id": "impact-001",
        "assessment_fingerprint": "c" * 64,
        "engineering_memory_generation_id": "generation-001",
    }

    assert build_report_id(**kwargs) == build_report_id(**kwargs)


def test_report_id_changes_with_lineage() -> None:
    first = build_report_id(
        mission_id="mission-001",
        mission_fingerprint="a" * 64,
        task_set_fingerprint="b" * 64,
        assessment_id="impact-001",
        assessment_fingerprint="c" * 64,
        engineering_memory_generation_id="generation-001",
    )
    second = build_report_id(
        mission_id="mission-001",
        mission_fingerprint="a" * 64,
        task_set_fingerprint="b" * 64,
        assessment_id="impact-001",
        assessment_fingerprint="c" * 64,
        engineering_memory_generation_id="generation-002",
    )

    assert first != second


def test_section_id_sorts_source_ids() -> None:
    first = build_section_id(
        report_id="report-001",
        section_type="mission",
        title="Mission",
        source_ids=("b", "a"),
    )
    second = build_section_id(
        report_id="report-001",
        section_type="mission",
        title="Mission",
        source_ids=("a", "b"),
    )

    assert first == second


def test_risk_id_changes_with_source() -> None:
    first = build_risk_id(
        report_id="report-001",
        source_type="finding",
        source_id="finding-001",
        title="Risk",
    )
    second = build_risk_id(
        report_id="report-001",
        source_type="finding",
        source_id="finding-002",
        title="Risk",
    )

    assert first != second


def test_traceability_id_is_deterministic() -> None:
    kwargs = {
        "report_id": "report-001",
        "source_type": "mission",
        "source_id": "mission-001",
        "target_type": "task",
        "target_id": "task-001",
        "relationship": "decomposes-to",
    }

    assert build_traceability_id(**kwargs) == build_traceability_id(**kwargs)


def test_component_fingerprints_are_repeatable() -> None:
    assert build_section_fingerprint(_section()) == build_section_fingerprint(_section())
    assert build_risk_fingerprint(_risk()) == build_risk_fingerprint(_risk())
    assert build_traceability_fingerprint(_traceability()) == build_traceability_fingerprint(
        _traceability()
    )


def test_report_fingerprint_ignores_existing_fingerprint() -> None:
    report = _report()
    changed = report.model_copy(update={"report_fingerprint": "f" * 64})

    assert build_report_fingerprint(report) == build_report_fingerprint(changed)


def test_ready_status_maps_to_ready() -> None:
    _, _, assessment = _inputs()
    assessment = assessment.model_copy(update={"status": DecisionStatus.READY})

    assert derive_report_status(assessment) is MissionReportStatus.READY


def test_conditional_statuses_map_to_conditional() -> None:
    _, _, assessment = _inputs()

    for status in (
        DecisionStatus.READY_WITH_CONDITIONS,
        DecisionStatus.APPROVAL_REQUIRED,
    ):
        candidate = assessment.model_copy(update={"status": status})
        assert derive_report_status(candidate) is MissionReportStatus.CONDITIONAL


def test_blocked_status_maps_to_blocked() -> None:
    _, _, assessment = _inputs()
    assessment = assessment.model_copy(update={"status": DecisionStatus.BLOCKED})

    assert derive_report_status(assessment) is MissionReportStatus.BLOCKED


def test_risk_severity_mapping_covers_all_values() -> None:
    expected = {
        ImpactSeverity.NONE: MissionReportRiskSeverity.LOW,
        ImpactSeverity.LOW: MissionReportRiskSeverity.LOW,
        ImpactSeverity.MEDIUM: MissionReportRiskSeverity.MEDIUM,
        ImpactSeverity.HIGH: MissionReportRiskSeverity.HIGH,
        ImpactSeverity.CRITICAL: MissionReportRiskSeverity.CRITICAL,
        ImpactSeverity.UNKNOWN: MissionReportRiskSeverity.MEDIUM,
    }

    assert {severity: map_risk_severity(severity) for severity in ImpactSeverity} == expected


def test_required_sections_respect_configuration() -> None:
    sections = required_section_types(
        include_engineering_memory=False,
        include_risks=False,
        include_traceability=False,
    )

    assert MissionReportSectionType.ENGINEERING_MEMORY not in sections
    assert MissionReportSectionType.RISKS not in sections
    assert MissionReportSectionType.TRACEABILITY not in sections
    assert sections[-1] is MissionReportSectionType.VALIDATION


def test_section_sort_key_matches_frozen_order() -> None:
    sections = required_section_types(
        include_engineering_memory=True,
        include_risks=True,
        include_traceability=True,
    )

    assert tuple(sorted(sections, key=section_sort_key)) == sections


def test_risk_inclusion_excludes_low_only() -> None:
    assert should_include_risk(MissionReportRiskSeverity.LOW) is False
    assert should_include_risk(MissionReportRiskSeverity.MEDIUM) is True
    assert should_include_risk(MissionReportRiskSeverity.HIGH) is True
    assert should_include_risk(MissionReportRiskSeverity.CRITICAL) is True
