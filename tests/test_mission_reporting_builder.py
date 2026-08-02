"""Mission Reporting builder tests."""

from pathlib import Path

import pytest

from forge.impact.models import DecisionStatus, ImpactSeverity
from forge.mission_reporting.builder import MissionReportBuilder
from forge.mission_reporting.errors import (
    MissionReportingDisabledError,
    MissionReportingValidationError,
)
from forge.mission_reporting.models import (
    MissionReport,
    MissionReportingConfiguration,
    MissionReportRiskSeverity,
    MissionReportSectionType,
    MissionReportStatus,
)
from forge.tasks.models import TaskStatus
from tests.test_engineering_memory_builder import _inputs
from tests.test_mission_reporting_validation import _memory_store


def _build(tmp_path: Path) -> MissionReport:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    report = MissionReportBuilder().build(
        mission,
        task_set,
        assessment,
        memory,
    )

    return report


def test_builder_creates_report(tmp_path: Path) -> None:
    report = _build(tmp_path)

    assert report.report_id.startswith("mission-report-")
    assert report.report_fingerprint != "pending"


def test_builder_is_deterministic(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)
    builder = MissionReportBuilder()

    first = builder.build(
        mission,
        task_set,
        assessment,
        memory,
    )
    second = builder.build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert first == second
    assert first.report_id == second.report_id
    assert first.report_fingerprint == second.report_fingerprint


def test_builder_preserves_lineage(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    report = MissionReportBuilder().build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert report.mission_id == mission.mission_id
    assert report.mission_fingerprint == mission.mission_fingerprint
    assert report.task_set_fingerprint == task_set.task_set_fingerprint
    assert report.assessment_id == assessment.assessment_id
    assert report.assessment_fingerprint == assessment.assessment_fingerprint
    assert report.engineering_memory_generation_id == (
        memory.generation.generation_id if memory.generation is not None else ""
    )


def test_builder_creates_required_sections(tmp_path: Path) -> None:
    report = _build(tmp_path)

    assert tuple(section.section_type for section in report.sections) == (
        MissionReportSectionType.EXECUTIVE_SUMMARY,
        MissionReportSectionType.MISSION,
        MissionReportSectionType.TASKS,
        MissionReportSectionType.IMPACT,
        MissionReportSectionType.ENGINEERING_MEMORY,
        MissionReportSectionType.RISKS,
        MissionReportSectionType.TRACEABILITY,
        MissionReportSectionType.VALIDATION,
    )


def test_builder_statistics_match_report(tmp_path: Path) -> None:
    report = _build(tmp_path)

    assert report.statistics.section_count == len(report.sections)
    assert report.statistics.risk_count == len(report.risks)
    assert report.statistics.traceability_count == len(report.traceability)


def test_builder_counts_blocked_tasks(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    blocked_task = task_set.tasks[0].model_copy(
        update={
            "status": TaskStatus.BLOCKED,
            "blocking_reason": "Dependency unavailable.",
        }
    )
    task_set = task_set.model_copy(
        update={
            "tasks": (
                blocked_task,
                *task_set.tasks[1:],
            )
        }
    )

    report = MissionReportBuilder().build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert report.statistics.blocked_task_count == 1


def test_builder_maps_ready_status(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)
    assessment = assessment.model_copy(update={"status": DecisionStatus.READY})

    report = MissionReportBuilder().build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert report.status is MissionReportStatus.READY


def test_builder_maps_conditional_status(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)
    assessment = assessment.model_copy(
        update={
            "status": DecisionStatus.READY_WITH_CONDITIONS,
        }
    )

    report = MissionReportBuilder().build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert report.status is MissionReportStatus.CONDITIONAL


def test_builder_maps_blocked_status(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)
    assessment = assessment.model_copy(
        update={
            "status": DecisionStatus.BLOCKED,
            "blocking_reason": "Critical impact unresolved.",
        }
    )

    report = MissionReportBuilder().build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert report.status is MissionReportStatus.BLOCKED


def test_builder_includes_medium_and_above_risks(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    finding = assessment.findings[0].model_copy(update={"severity": ImpactSeverity.HIGH})
    assessment = assessment.model_copy(update={"findings": (finding,)})

    report = MissionReportBuilder().build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert any(risk.severity is MissionReportRiskSeverity.HIGH for risk in report.risks)


def test_builder_excludes_low_risks(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    finding = assessment.findings[0].model_copy(update={"severity": ImpactSeverity.LOW})
    assessment = assessment.model_copy(update={"findings": (finding,)})

    report = MissionReportBuilder().build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert all(risk.source_id != finding.finding_id for risk in report.risks)


def test_builder_can_exclude_risks(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    builder = MissionReportBuilder(
        MissionReportingConfiguration(
            include_risks=False,
        )
    )

    report = builder.build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert report.risks == ()
    assert MissionReportSectionType.RISKS not in {
        section.section_type for section in report.sections
    }


def test_builder_can_exclude_traceability(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    builder = MissionReportBuilder(
        MissionReportingConfiguration(
            include_traceability=False,
        )
    )

    report = builder.build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert report.traceability == ()
    assert MissionReportSectionType.TRACEABILITY not in {
        section.section_type for section in report.sections
    }


def test_builder_can_exclude_engineering_memory_section(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    builder = MissionReportBuilder(
        MissionReportingConfiguration(
            include_engineering_memory=False,
        )
    )

    report = builder.build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert MissionReportSectionType.ENGINEERING_MEMORY not in {
        section.section_type for section in report.sections
    }


def test_builder_respects_risk_limit(tmp_path: Path) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    builder = MissionReportBuilder(
        MissionReportingConfiguration(
            max_risks=1,
        )
    )

    report = builder.build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert len(report.risks) <= 1


def test_builder_respects_traceability_limit(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    builder = MissionReportBuilder(
        MissionReportingConfiguration(
            max_traceability_items=1,
        )
    )

    report = builder.build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert len(report.traceability) <= 1


def test_builder_rejects_disabled_configuration(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    builder = MissionReportBuilder(
        MissionReportingConfiguration(
            enabled=False,
        )
    )

    with pytest.raises(MissionReportingDisabledError):
        builder.build(
            mission,
            task_set,
            assessment,
            memory,
        )


def test_builder_rejects_invalid_lineage(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    task_set = task_set.model_copy(update={"mission_id": "mission-invalid"})

    with pytest.raises(MissionReportingValidationError):
        MissionReportBuilder().build(
            mission,
            task_set,
            assessment,
            memory,
        )


def test_builder_source_fingerprints_are_complete(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)

    assert tuple(report.source_fingerprints) == (
        "assessment",
        "engineering_memory",
        "mission",
        "task_set",
    )


def test_builder_report_title_contains_target_name(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    report = MissionReportBuilder().build(
        mission,
        task_set,
        assessment,
        memory,
    )

    assert mission.target_name in report.title


def test_builder_traceability_contains_tasks(
    tmp_path: Path,
) -> None:
    mission, task_set, assessment = _inputs()
    memory = _memory_store(tmp_path)

    report = MissionReportBuilder().build(
        mission,
        task_set,
        assessment,
        memory,
    )

    targets = {item.target_id for item in report.traceability if item.target_type == "task"}

    assert {task.task_id for task in task_set.tasks}.issubset(targets)
