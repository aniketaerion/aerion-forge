"""Aggregate validation for Impact Decision assessments."""

from collections import Counter

from forge.impact.identifiers import (
    build_assessment_fingerprint,
    validate_assessment_id,
    validate_fingerprint,
)
from forge.impact.models import (
    DecisionStatus,
    ImpactAssessment,
    ImpactDecisionConfiguration,
    ImpactSeverity,
    ImpactStatistics,
    ImpactValidationMessage,
    ImpactValidationResult,
    ImpactValidationSeverity,
)
from forge.impact.policies import highest_severity


def _message(
    *,
    severity: ImpactValidationSeverity,
    field: str,
    message: str,
    assessment_id: str | None = None,
) -> ImpactValidationMessage:
    return ImpactValidationMessage(
        severity=severity,
        field=field,
        message=message,
        assessment_id=assessment_id,
    )


def calculate_statistics(
    assessment: ImpactAssessment,
) -> ImpactStatistics:
    """Calculate deterministic assessment statistics."""

    task_ids = {task_id for finding in assessment.findings for task_id in finding.affected_task_ids}
    components = {
        component for finding in assessment.findings for component in finding.affected_components
    }
    severities = Counter(finding.severity for finding in assessment.findings)

    return ImpactStatistics(
        finding_count=len(assessment.findings),
        affected_task_count=len(task_ids),
        affected_component_count=len(components),
        high_impact_count=severities[ImpactSeverity.HIGH],
        critical_impact_count=severities[ImpactSeverity.CRITICAL],
    )


def validate_assessment(
    assessment: ImpactAssessment,
    configuration: ImpactDecisionConfiguration | None = None,
) -> ImpactValidationResult:
    """Validate one assessment without mutation."""

    active = configuration if configuration is not None else ImpactDecisionConfiguration()
    messages: list[ImpactValidationMessage] = []
    assessment_id = assessment.assessment_id

    if not active.enabled:
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="configuration.enabled",
                message="Impact Decision is disabled.",
                assessment_id=assessment_id,
            )
        )

    if not validate_assessment_id(assessment_id):
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="assessment_id",
                message="Assessment ID is not canonical.",
                assessment_id=assessment_id,
            )
        )

    if not validate_fingerprint(assessment.assessment_fingerprint):
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="assessment_fingerprint",
                message="Assessment fingerprint is not canonical.",
                assessment_id=assessment_id,
            )
        )
    else:
        expected_fingerprint = build_assessment_fingerprint(assessment)

        if expected_fingerprint != assessment.assessment_fingerprint:
            messages.append(
                _message(
                    severity=ImpactValidationSeverity.ERROR,
                    field="assessment_fingerprint",
                    message="Assessment fingerprint mismatch.",
                    assessment_id=assessment_id,
                )
            )

    if len(assessment.findings) > active.max_findings:
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="findings",
                message="Assessment exceeds maximum findings.",
                assessment_id=assessment_id,
            )
        )

    if len(assessment.recommendation.options) > active.max_options:
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="recommendation.options",
                message="Recommendation exceeds maximum options.",
                assessment_id=assessment_id,
            )
        )

    finding_ids = [finding.finding_id for finding in assessment.findings]

    if len(finding_ids) != len(set(finding_ids)):
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="findings",
                message="Finding IDs must be unique.",
                assessment_id=assessment_id,
            )
        )

    if finding_ids != sorted(finding_ids):
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="findings",
                message="Findings must use canonical ordering.",
                assessment_id=assessment_id,
            )
        )

    option_ids = [option.option_id for option in assessment.recommendation.options]

    if option_ids != sorted(option_ids):
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="recommendation.options",
                message="Decision options must use canonical ordering.",
                assessment_id=assessment_id,
            )
        )

    assessment_tasks = set(assessment.task_ids)
    referenced_tasks = {
        task_id for finding in assessment.findings for task_id in finding.affected_task_ids
    }
    unknown_tasks = sorted(referenced_tasks - assessment_tasks)

    if unknown_tasks:
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="findings.affected_task_ids",
                message=(
                    "Findings reference tasks outside the assessment: " + ", ".join(unknown_tasks)
                ),
                assessment_id=assessment_id,
            )
        )

    if len(assessment.task_ids) > active.max_affected_tasks:
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="task_ids",
                message="Assessment exceeds maximum affected tasks.",
                assessment_id=assessment_id,
            )
        )

    affected_components = {
        component for finding in assessment.findings for component in finding.affected_components
    }

    if len(affected_components) > active.max_affected_components:
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="findings.affected_components",
                message=("Assessment exceeds maximum affected components."),
                assessment_id=assessment_id,
            )
        )

    expected_severity = highest_severity(tuple(finding.severity for finding in assessment.findings))

    if assessment.overall_severity is not expected_severity:
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="overall_severity",
                message=("Overall severity does not match findings."),
                assessment_id=assessment_id,
            )
        )

    expected_statistics = calculate_statistics(assessment)

    if assessment.statistics != expected_statistics:
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="statistics",
                message="Impact statistics do not match findings.",
                assessment_id=assessment_id,
            )
        )

    severe = assessment.overall_severity in {
        ImpactSeverity.HIGH,
        ImpactSeverity.CRITICAL,
    }

    if (
        severe
        and active.require_approval_for_high_impact
        and not assessment.recommendation.approval_requirements
    ):
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="recommendation.approval_requirements",
                message=("High or critical impact requires approval."),
                assessment_id=assessment_id,
            )
        )

    if (
        active.require_validation_requirements
        and not assessment.recommendation.validation_requirements
    ):
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="recommendation.validation_requirements",
                message=("Decision recommendations require validation."),
                assessment_id=assessment_id,
            )
        )

    if assessment.status is DecisionStatus.BLOCKED and not assessment.blocking_reason:
        messages.append(
            _message(
                severity=ImpactValidationSeverity.ERROR,
                field="blocking_reason",
                message="Blocked decisions require a reason.",
                assessment_id=assessment_id,
            )
        )

    return ImpactValidationResult(
        valid=not any(message.severity is ImpactValidationSeverity.ERROR for message in messages),
        messages=tuple(messages),
    )
