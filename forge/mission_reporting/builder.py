"""Deterministic Mission Reporting builder."""

from forge.engineering_memory.models import EngineeringMemoryStore
from forge.impact.models import ImpactAssessment
from forge.mission_reporting.identifiers import (
    build_report_fingerprint,
    build_report_id,
    build_risk_id,
    build_section_id,
    build_traceability_id,
)
from forge.mission_reporting.models import (
    MissionReport,
    MissionReportingConfiguration,
    MissionReportingValidationResult,
    MissionReportRisk,
    MissionReportRiskSeverity,
    MissionReportSection,
    MissionReportSectionType,
    MissionReportStatistics,
    MissionTraceabilityItem,
)
from forge.mission_reporting.policies import (
    derive_report_status,
    map_risk_severity,
    required_section_types,
    section_sort_key,
    should_include_risk,
)
from forge.mission_reporting.validator import MissionReportingValidator
from forge.planning.models import MissionPlan, MissionRiskLevel
from forge.tasks.models import TaskSet, TaskStatus


class MissionReportBuilder:
    """Build one deterministic Mission Report."""

    def __init__(
        self,
        configuration: MissionReportingConfiguration | None = None,
    ) -> None:
        self.configuration = (
            configuration if configuration is not None else MissionReportingConfiguration()
        )
        self.validator = MissionReportingValidator(self.configuration)

    def build(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
        engineering_memory: EngineeringMemoryStore,
    ) -> MissionReport:
        """Build a validated deterministic report."""

        validation = self.validator.validate_or_raise(
            mission,
            task_set,
            assessment,
            engineering_memory,
        )

        if engineering_memory.generation is None:
            raise RuntimeError("Engineering Memory generation is required.")

        report_id = build_report_id(
            mission_id=mission.mission_id,
            mission_fingerprint=mission.mission_fingerprint,
            task_set_fingerprint=task_set.task_set_fingerprint,
            assessment_id=assessment.assessment_id,
            assessment_fingerprint=(assessment.assessment_fingerprint),
            engineering_memory_generation_id=(engineering_memory.generation.generation_id),
        )

        risks = self._build_risks(
            report_id,
            mission,
            assessment,
        )

        traceability = self._build_traceability(
            report_id,
            mission,
            task_set,
            assessment,
        )

        sections = self._build_sections(
            report_id,
            mission,
            task_set,
            assessment,
            engineering_memory,
            validation,
            risks,
            traceability,
        )

        blocked_task_count = sum(task.status is TaskStatus.BLOCKED for task in task_set.tasks)

        statistics = MissionReportStatistics(
            task_count=len(task_set.tasks),
            blocked_task_count=blocked_task_count,
            risk_count=len(risks),
            high_risk_count=sum(risk.severity is MissionReportRiskSeverity.HIGH for risk in risks),
            critical_risk_count=sum(
                risk.severity is MissionReportRiskSeverity.CRITICAL for risk in risks
            ),
            traceability_count=len(traceability),
            section_count=len(sections),
            engineering_memory_record_count=len(engineering_memory.records),
        )

        source_fingerprints = {
            "assessment": assessment.assessment_fingerprint,
            "engineering_memory": (engineering_memory.generation.store_fingerprint),
            "mission": mission.mission_fingerprint,
            "task_set": task_set.task_set_fingerprint,
        }

        provisional = MissionReport(
            report_id=report_id,
            mission_id=mission.mission_id,
            mission_fingerprint=mission.mission_fingerprint,
            task_set_fingerprint=task_set.task_set_fingerprint,
            assessment_id=assessment.assessment_id,
            assessment_fingerprint=(assessment.assessment_fingerprint),
            engineering_memory_generation_id=(engineering_memory.generation.generation_id),
            title=f"Mission Report — {mission.target_name}",
            executive_summary=self._executive_summary(
                mission,
                task_set,
                assessment,
                blocked_task_count,
            ),
            status=derive_report_status(assessment),
            sections=sections,
            risks=risks,
            traceability=traceability,
            statistics=statistics,
            source_fingerprints=source_fingerprints,
            report_fingerprint="pending",
        )

        return provisional.model_copy(
            update={"report_fingerprint": build_report_fingerprint(provisional)}
        )

    def _build_risks(
        self,
        report_id: str,
        mission: MissionPlan,
        assessment: ImpactAssessment,
    ) -> tuple[MissionReportRisk, ...]:
        risks: list[MissionReportRisk] = []

        mission_severity = {
            MissionRiskLevel.LOW: MissionReportRiskSeverity.LOW,
            MissionRiskLevel.MEDIUM: MissionReportRiskSeverity.MEDIUM,
            MissionRiskLevel.HIGH: MissionReportRiskSeverity.HIGH,
            MissionRiskLevel.CRITICAL: (MissionReportRiskSeverity.CRITICAL),
            MissionRiskLevel.UNKNOWN: (MissionReportRiskSeverity.MEDIUM),
        }

        if self.configuration.include_risks:
            for source in mission.risks:
                severity = mission_severity[source.level]

                if not should_include_risk(severity):
                    continue

                risks.append(
                    MissionReportRisk(
                        risk_id=build_risk_id(
                            report_id=report_id,
                            source_type="mission-risk",
                            source_id=source.risk_id,
                            title=source.statement,
                        ),
                        title=source.statement,
                        description=source.evidence,
                        severity=severity,
                        source_type="mission-risk",
                        source_id=source.risk_id,
                        mitigation=source.mitigation,
                    )
                )

            for finding in assessment.findings:
                severity = map_risk_severity(finding.severity)

                if not should_include_risk(severity):
                    continue

                risks.append(
                    MissionReportRisk(
                        risk_id=build_risk_id(
                            report_id=report_id,
                            source_type="impact-finding",
                            source_id=finding.finding_id,
                            title=finding.summary,
                        ),
                        title=finding.summary,
                        description=finding.rationale,
                        severity=severity,
                        source_type="impact-finding",
                        source_id=finding.finding_id,
                        affected_task_ids=(finding.affected_task_ids),
                    )
                )

        ordered = sorted(
            risks,
            key=lambda risk: (
                risk.severity.value,
                risk.risk_id,
            ),
        )

        return tuple(ordered[: self.configuration.max_risks])

    def _build_traceability(
        self,
        report_id: str,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
    ) -> tuple[MissionTraceabilityItem, ...]:
        if not self.configuration.include_traceability:
            return ()

        items: list[MissionTraceabilityItem] = []

        for task in task_set.tasks:
            items.append(
                MissionTraceabilityItem(
                    traceability_id=build_traceability_id(
                        report_id=report_id,
                        source_type="mission",
                        source_id=mission.mission_id,
                        target_type="task",
                        target_id=task.task_id,
                        relationship="decomposes-to",
                    ),
                    source_type="mission",
                    source_id=mission.mission_id,
                    target_type="task",
                    target_id=task.task_id,
                    relationship="decomposes-to",
                )
            )

        for finding in assessment.findings:
            for task_id in finding.affected_task_ids:
                items.append(
                    MissionTraceabilityItem(
                        traceability_id=(
                            build_traceability_id(
                                report_id=report_id,
                                source_type="impact-finding",
                                source_id=finding.finding_id,
                                target_type="task",
                                target_id=task_id,
                                relationship="affects",
                            )
                        ),
                        source_type="impact-finding",
                        source_id=finding.finding_id,
                        target_type="task",
                        target_id=task_id,
                        relationship="affects",
                        evidence_ids=(finding.evidence_references),
                    )
                )

        return tuple(
            sorted(
                items,
                key=lambda item: item.traceability_id,
            )[: self.configuration.max_traceability_items]
        )

    def _build_sections(
        self,
        report_id: str,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
        engineering_memory: EngineeringMemoryStore,
        validation: MissionReportingValidationResult,
        risks: tuple[MissionReportRisk, ...],
        traceability: tuple[MissionTraceabilityItem, ...],
    ) -> tuple[MissionReportSection, ...]:
        section_types = required_section_types(
            include_engineering_memory=(self.configuration.include_engineering_memory),
            include_risks=self.configuration.include_risks,
            include_traceability=(self.configuration.include_traceability),
        )

        content_by_type = {
            MissionReportSectionType.EXECUTIVE_SUMMARY: (
                "Executive Summary",
                self._executive_summary(
                    mission,
                    task_set,
                    assessment,
                    task_set.statistics.blocked_tasks,
                ),
                (),
                (
                    mission.mission_id,
                    assessment.assessment_id,
                ),
            ),
            MissionReportSectionType.MISSION: (
                "Mission",
                mission.objective.statement,
                tuple(deliverable.description for deliverable in mission.deliverables),
                (mission.mission_id,),
            ),
            MissionReportSectionType.TASKS: (
                "Tasks",
                f"{len(task_set.tasks)} deterministic tasks.",
                tuple(
                    f"{task.task_id}: {task.title} [{task.status.value}]"
                    for task in sorted(
                        task_set.tasks,
                        key=lambda item: item.sequence,
                    )
                ),
                tuple(task.task_id for task in task_set.tasks),
            ),
            MissionReportSectionType.IMPACT: (
                "Impact Decision",
                assessment.recommendation.rationale,
                tuple(finding.summary for finding in assessment.findings),
                (assessment.assessment_id,),
            ),
            MissionReportSectionType.ENGINEERING_MEMORY: (
                "Engineering Memory",
                (f"{len(engineering_memory.records)} verified memory records."),
                tuple(
                    record.title
                    for record in sorted(
                        engineering_memory.records.values(),
                        key=lambda item: item.memory_id,
                    )
                ),
                tuple(sorted(engineering_memory.records)),
            ),
            MissionReportSectionType.RISKS: (
                "Risks",
                f"{len(risks)} included risks.",
                tuple(f"{risk.severity.value}: {risk.title}" for risk in risks),
                tuple(risk.risk_id for risk in risks),
            ),
            MissionReportSectionType.TRACEABILITY: (
                "Traceability",
                (f"{len(traceability)} traceability relationships."),
                tuple(
                    f"{item.source_id} {item.relationship} {item.target_id}"
                    for item in traceability
                ),
                tuple(item.traceability_id for item in traceability),
            ),
            MissionReportSectionType.VALIDATION: (
                "Validation",
                ("Mission Reporting inputs passed deterministic validation."),
                tuple(
                    f"{message.severity.value}: {message.code} — {message.message}"
                    for message in validation.messages
                )
                or ("No validation findings.",),
                tuple(message.code for message in validation.messages),
            ),
        }

        sections: list[MissionReportSection] = []

        for section_type in section_types:
            title, summary, content, source_ids = content_by_type[section_type]

            sections.append(
                MissionReportSection(
                    section_id=build_section_id(
                        report_id=report_id,
                        section_type=section_type.value,
                        title=title,
                        source_ids=source_ids,
                    ),
                    section_type=section_type,
                    title=title,
                    summary=summary,
                    content=content,
                    source_ids=source_ids,
                )
            )

        return tuple(
            sorted(
                sections,
                key=lambda section: section_sort_key(section.section_type),
            )[: self.configuration.max_sections]
        )

    def _executive_summary(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
        assessment: ImpactAssessment,
        blocked_task_count: int,
    ) -> str:
        return (
            f"Mission '{mission.objective.statement}' contains "
            f"{len(task_set.tasks)} tasks, "
            f"{blocked_task_count} blocked tasks, and "
            f"{len(assessment.findings)} impact findings. "
            f"Decision status: {assessment.status.value}."
        )
