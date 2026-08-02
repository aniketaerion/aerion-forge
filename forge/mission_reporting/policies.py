"""Deterministic Mission Reporting policies."""

from forge.impact.models import (
    DecisionStatus,
    ImpactAssessment,
    ImpactSeverity,
)
from forge.mission_reporting.models import (
    MissionReportRiskSeverity,
    MissionReportSectionType,
    MissionReportStatus,
)

SECTION_ORDER = (
    MissionReportSectionType.EXECUTIVE_SUMMARY,
    MissionReportSectionType.MISSION,
    MissionReportSectionType.TASKS,
    MissionReportSectionType.IMPACT,
    MissionReportSectionType.ENGINEERING_MEMORY,
    MissionReportSectionType.RISKS,
    MissionReportSectionType.TRACEABILITY,
    MissionReportSectionType.VALIDATION,
)


def derive_report_status(
    assessment: ImpactAssessment,
) -> MissionReportStatus:
    """Derive report readiness from the persisted Impact Assessment."""

    if assessment.status is DecisionStatus.BLOCKED:
        return MissionReportStatus.BLOCKED

    if assessment.status in {
        DecisionStatus.READY_WITH_CONDITIONS,
        DecisionStatus.APPROVAL_REQUIRED,
    }:
        return MissionReportStatus.CONDITIONAL

    return MissionReportStatus.READY


def map_risk_severity(
    severity: ImpactSeverity,
) -> MissionReportRiskSeverity:
    """Map Impact severity into Mission Reporting severity."""

    mapping = {
        ImpactSeverity.NONE: MissionReportRiskSeverity.LOW,
        ImpactSeverity.LOW: MissionReportRiskSeverity.LOW,
        ImpactSeverity.MEDIUM: MissionReportRiskSeverity.MEDIUM,
        ImpactSeverity.HIGH: MissionReportRiskSeverity.HIGH,
        ImpactSeverity.CRITICAL: MissionReportRiskSeverity.CRITICAL,
        ImpactSeverity.UNKNOWN: MissionReportRiskSeverity.MEDIUM,
    }

    return mapping[severity]


def required_section_types(
    *,
    include_engineering_memory: bool,
    include_risks: bool,
    include_traceability: bool,
) -> tuple[MissionReportSectionType, ...]:
    """Return the deterministic required section sequence."""

    required = [
        MissionReportSectionType.EXECUTIVE_SUMMARY,
        MissionReportSectionType.MISSION,
        MissionReportSectionType.TASKS,
        MissionReportSectionType.IMPACT,
    ]

    if include_engineering_memory:
        required.append(MissionReportSectionType.ENGINEERING_MEMORY)

    if include_risks:
        required.append(MissionReportSectionType.RISKS)

    if include_traceability:
        required.append(MissionReportSectionType.TRACEABILITY)

    required.append(MissionReportSectionType.VALIDATION)

    return tuple(required)


def section_sort_key(
    section_type: MissionReportSectionType,
) -> int:
    """Return the stable section ordering key."""

    return SECTION_ORDER.index(section_type)


def should_include_risk(
    severity: MissionReportRiskSeverity,
) -> bool:
    """Return whether a normalized risk belongs in the report."""

    return severity in {
        MissionReportRiskSeverity.MEDIUM,
        MissionReportRiskSeverity.HIGH,
        MissionReportRiskSeverity.CRITICAL,
    }
