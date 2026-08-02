"""Deterministic Impact Assessment construction."""

from forge.impact.errors import ImpactValidationError
from forge.impact.identifiers import (
    build_assessment_fingerprint,
    build_assessment_id,
)
from forge.impact.models import (
    DecisionApprovalRequirement,
    DecisionConfidence,
    DecisionOption,
    DecisionRecommendation,
    DecisionStatus,
    DecisionType,
    DecisionValidationRequirement,
    ImpactApprovalLevel,
    ImpactAssessment,
    ImpactCategory,
    ImpactDecisionConfiguration,
    ImpactFinding,
    ImpactScope,
    ImpactSeverity,
    ImpactStatistics,
    ImpactValidationCategory,
)
from forge.impact.policies import highest_severity
from forge.impact.validator import (
    calculate_statistics,
    validate_assessment,
)
from forge.planning.models import MissionPlan
from forge.tasks.models import (
    EngineeringTask,
    TaskRiskLevel,
    TaskSet,
    TaskStatus,
)

_RISK_MAPPING = {
    TaskRiskLevel.CRITICAL: ImpactSeverity.CRITICAL,
    TaskRiskLevel.HIGH: ImpactSeverity.HIGH,
    TaskRiskLevel.MEDIUM: ImpactSeverity.MEDIUM,
    TaskRiskLevel.LOW: ImpactSeverity.LOW,
    TaskRiskLevel.UNKNOWN: ImpactSeverity.UNKNOWN,
}


class ImpactAssessmentBuilder:
    """Build a valid deterministic assessment from persisted plans and tasks."""

    def __init__(
        self,
        configuration: ImpactDecisionConfiguration | None = None,
    ) -> None:
        self.configuration = (
            configuration if configuration is not None else ImpactDecisionConfiguration()
        )

    def build(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
    ) -> ImpactAssessment:
        """Build and validate one canonical impact assessment."""

        self._validate_inputs(mission, task_set)

        tasks = tuple(
            sorted(
                task_set.tasks,
                key=lambda task: task.task_id,
            )
        )
        findings = self._build_findings(tasks)
        severity = highest_severity(tuple(finding.severity for finding in findings))
        status = self._derive_status(tasks, severity)
        recommendation = self._build_recommendation(
            tasks=tasks,
            status=status,
            severity=severity,
        )
        blocking_reason = self._blocking_reason(
            tasks,
            status,
            severity,
        )

        assessment_id = build_assessment_id(
            mission_id=mission.mission_id,
            task_set_fingerprint=task_set.task_set_fingerprint,
            title=mission.objective.statement,
            sequence=1,
        )

        draft = ImpactAssessment(
            assessment_id=assessment_id,
            assessment_fingerprint="0" * 64,
            mission_id=mission.mission_id,
            task_set_fingerprint=task_set.task_set_fingerprint,
            task_ids=tuple(task.task_id for task in tasks),
            findings=findings,
            recommendation=recommendation,
            status=status,
            confidence=self._derive_confidence(severity),
            overall_severity=severity,
            statistics=self._temporary_statistics(),
            blocking_reason=blocking_reason,
            source_fingerprints=self._source_fingerprints(
                mission,
                task_set,
            ),
        )

        with_statistics = draft.model_copy(
            update={
                "statistics": calculate_statistics(draft),
            }
        )
        assessment = with_statistics.model_copy(
            update={
                "assessment_fingerprint": (build_assessment_fingerprint(with_statistics)),
            }
        )

        validation = validate_assessment(
            assessment,
            self.configuration,
        )

        if not validation.valid:
            details = "; ".join(
                f"{message.field}: {message.message}" for message in validation.messages
            )
            raise ImpactValidationError(f"Generated impact assessment is invalid: {details}")

        return assessment

    def _validate_inputs(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
    ) -> None:
        if mission.mission_id != task_set.mission_id:
            raise ImpactValidationError("Mission ID does not match the Task Set.")

        if mission.mission_fingerprint != task_set.mission_fingerprint:
            raise ImpactValidationError("Mission fingerprint does not match the Task Set.")

        if not task_set.tasks:
            raise ImpactValidationError("Impact assessment requires at least one task.")

        task_ids = [task.task_id for task in task_set.tasks]

        if len(task_ids) != len(set(task_ids)):
            raise ImpactValidationError("Task IDs must be unique.")

        invalid_missions = sorted(
            {task.mission_id for task in task_set.tasks if task.mission_id != mission.mission_id}
        )

        if invalid_missions:
            raise ImpactValidationError("Task Set contains tasks belonging to another mission.")

    def _build_findings(
        self,
        tasks: tuple[EngineeringTask, ...],
    ) -> tuple[ImpactFinding, ...]:
        findings = tuple(self._finding(task) for task in tasks)

        return tuple(
            sorted(
                findings,
                key=lambda finding: finding.finding_id,
            )
        )

    def _finding(
        self,
        task: EngineeringTask,
    ) -> ImpactFinding:
        components = tuple(
            sorted({reference.canonical_name for reference in task.source_references})
        )
        evidence = tuple(sorted({reference.reference_id for reference in task.source_references}))

        return ImpactFinding(
            finding_id=f"finding-{task.task_id}",
            category=ImpactCategory.ARCHITECTURE,
            scope=ImpactScope.TASK,
            severity=_RISK_MAPPING[task.risk_level],
            summary=task.title,
            rationale=task.description,
            affected_task_ids=(task.task_id,),
            affected_components=components,
            evidence_references=evidence,
        )

    def _derive_status(
        self,
        tasks: tuple[EngineeringTask, ...],
        severity: ImpactSeverity,
    ) -> DecisionStatus:
        if any(task.status is TaskStatus.BLOCKED for task in tasks):
            return DecisionStatus.BLOCKED

        if severity is ImpactSeverity.UNKNOWN:
            return DecisionStatus.BLOCKED

        if severity in {
            ImpactSeverity.HIGH,
            ImpactSeverity.CRITICAL,
        }:
            return DecisionStatus.APPROVAL_REQUIRED

        if severity is ImpactSeverity.MEDIUM:
            return DecisionStatus.READY_WITH_CONDITIONS

        return DecisionStatus.READY

    def _build_recommendation(
        self,
        *,
        tasks: tuple[EngineeringTask, ...],
        status: DecisionStatus,
        severity: ImpactSeverity,
    ) -> DecisionRecommendation:
        options = tuple(
            sorted(
                (
                    DecisionOption(
                        option_id="option-escalate",
                        title="Escalate for Approval",
                        description=("Escalate the proposed work for required human approval."),
                        decision_type=DecisionType.ESCALATE,
                    ),
                    DecisionOption(
                        option_id="option-investigate",
                        title="Investigate",
                        description=("Resolve blocking or uncertain conditions before proceeding."),
                        decision_type=DecisionType.INVESTIGATE,
                    ),
                    DecisionOption(
                        option_id="option-proceed",
                        title="Proceed",
                        description=("Proceed under the approved task contract."),
                        decision_type=DecisionType.PROCEED,
                    ),
                    DecisionOption(
                        option_id="option-proceed-conditions",
                        title="Proceed with Conditions",
                        description=(
                            "Proceed only after all declared validation conditions are satisfied."
                        ),
                        decision_type=(DecisionType.PROCEED_WITH_CONDITIONS),
                    ),
                ),
                key=lambda option: option.option_id,
            )
        )

        selected = {
            DecisionStatus.READY: "option-proceed",
            DecisionStatus.READY_WITH_CONDITIONS: ("option-proceed-conditions"),
            DecisionStatus.APPROVAL_REQUIRED: "option-escalate",
            DecisionStatus.BLOCKED: "option-investigate",
        }[status]

        approvals = self._approvals(tasks, severity)
        validations = self._validations(tasks)

        return DecisionRecommendation(
            recommendation_id="recommendation-primary",
            selected_option_id=selected,
            options=options,
            rationale=(
                "Recommendation derived deterministically from task "
                f"status and {severity.value} impact severity."
            ),
            confidence=self._derive_confidence(severity),
            approval_requirements=approvals,
            validation_requirements=validations,
            conditions=tuple(
                requirement.description for requirement in validations if requirement.blocking
            ),
        )

    def _approvals(
        self,
        tasks: tuple[EngineeringTask, ...],
        severity: ImpactSeverity,
    ) -> tuple[DecisionApprovalRequirement, ...]:
        values: dict[
            ImpactApprovalLevel,
            DecisionApprovalRequirement,
        ] = {}

        for task in tasks:
            for approval in task.approval_requirements:
                level = ImpactApprovalLevel(approval.level.value)
                values[level] = DecisionApprovalRequirement(
                    requirement_id=approval.approval_id,
                    level=level,
                    reason=approval.reason,
                )

        if (
            severity
            in {
                ImpactSeverity.HIGH,
                ImpactSeverity.CRITICAL,
            }
            and ImpactApprovalLevel.HIGH_RISK_APPROVAL not in values
        ):
            level = ImpactApprovalLevel.HIGH_RISK_APPROVAL
            values[level] = DecisionApprovalRequirement(
                requirement_id="approval-high-risk",
                level=level,
                reason=("High or critical impact requires explicit human approval."),
            )

        return tuple(
            values[level]
            for level in sorted(
                values,
                key=lambda item: item.value,
            )
        )

    def _validations(
        self,
        tasks: tuple[EngineeringTask, ...],
    ) -> tuple[DecisionValidationRequirement, ...]:
        values: dict[
            str,
            DecisionValidationRequirement,
        ] = {}

        for task in tasks:
            for requirement in task.validation_requirements:
                values[requirement.requirement_id] = DecisionValidationRequirement(
                    requirement_id=(requirement.requirement_id),
                    category=ImpactValidationCategory(requirement.category.value),
                    description=requirement.description,
                    blocking=requirement.mandatory,
                )

        if not values:
            values["validation-manual-review"] = DecisionValidationRequirement(
                requirement_id=("validation-manual-review"),
                category=(ImpactValidationCategory.MANUAL_REVIEW),
                description=("Review the proposed impact decision manually."),
                blocking=True,
            )

        return tuple(values[key] for key in sorted(values))

    def _derive_confidence(
        self,
        severity: ImpactSeverity,
    ) -> DecisionConfidence:
        if severity is ImpactSeverity.UNKNOWN:
            return DecisionConfidence.INSUFFICIENT

        return DecisionConfidence.HIGH

    def _blocking_reason(
        self,
        tasks: tuple[EngineeringTask, ...],
        status: DecisionStatus,
        severity: ImpactSeverity,
    ) -> str | None:
        if status is not DecisionStatus.BLOCKED:
            return None

        blocked = tuple(task.task_id for task in tasks if task.status is TaskStatus.BLOCKED)

        if blocked:
            return "Blocked task conditions must be resolved: " + ", ".join(blocked)

        if severity is ImpactSeverity.UNKNOWN:
            return "Impact severity is unknown and requires investigation."

        return "Impact decision is blocked."

    def _source_fingerprints(
        self,
        mission: MissionPlan,
        task_set: TaskSet,
    ) -> dict[str, str]:
        values = dict(mission.source_fingerprints)
        values.update(task_set.source_fingerprints)
        values["mission"] = mission.mission_fingerprint
        values["task_set"] = task_set.task_set_fingerprint

        return {key: values[key] for key in sorted(values)}

    def _temporary_statistics(self) -> ImpactStatistics:
        return ImpactStatistics(
            finding_count=0,
            affected_task_count=0,
            affected_component_count=0,
            high_impact_count=0,
            critical_impact_count=0,
        )
