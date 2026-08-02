"""Impact aggregate-validation tests."""

from typing import Any

from forge.impact.identifiers import (
    build_assessment_fingerprint,
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
from forge.impact.validator import (
    calculate_statistics,
    validate_assessment,
)


def _validation() -> DecisionValidationRequirement:
    return DecisionValidationRequirement(
        requirement_id="validation-1",
        category=ImpactValidationCategory.UNIT_TESTING,
        description="Unit tests must pass.",
    )


def _approval() -> DecisionApprovalRequirement:
    return DecisionApprovalRequirement(
        requirement_id="approval-1",
        level=ImpactApprovalLevel.HIGH_RISK_APPROVAL,
        reason="High-impact approval is required.",
    )


def _option(
    option_id: str = "option-1",
) -> DecisionOption:
    return DecisionOption(
        option_id=option_id,
        title=option_id,
        description="Controlled option.",
        decision_type=DecisionType.PROCEED,
    )


def _finding(
    *,
    finding_id: str = "finding-1",
    task_id: str = "task-1",
    severity: ImpactSeverity = ImpactSeverity.MEDIUM,
) -> ImpactFinding:
    return ImpactFinding(
        finding_id=finding_id,
        category=ImpactCategory.ARCHITECTURE,
        scope=ImpactScope.TASK,
        severity=severity,
        summary="Task behavior is affected.",
        rationale="The task contract changes.",
        affected_task_ids=(task_id,),
    )


def _assessment(**updates: Any) -> ImpactAssessment:
    finding = _finding()
    recommendation = DecisionRecommendation(
        recommendation_id="recommendation-1",
        selected_option_id="option-1",
        options=(_option(),),
        rationale="Proceed with controlled validation.",
        confidence=DecisionConfidence.HIGH,
        validation_requirements=(_validation(),),
    )
    values: dict[str, Any] = {
        "assessment_id": "impact-" + "a" * 20,
        "assessment_fingerprint": "0" * 64,
        "mission_id": "mission-1",
        "task_set_fingerprint": "b" * 64,
        "task_ids": ("task-1",),
        "findings": (finding,),
        "recommendation": recommendation,
        "status": DecisionStatus.READY,
        "confidence": DecisionConfidence.HIGH,
        "overall_severity": ImpactSeverity.MEDIUM,
        "statistics": ImpactStatistics(
            finding_count=1,
            affected_task_count=1,
            affected_component_count=0,
            high_impact_count=0,
            critical_impact_count=0,
        ),
    }
    values.update(updates)
    draft = ImpactAssessment(**values)
    return draft.model_copy(
        update={"assessment_fingerprint": (build_assessment_fingerprint(draft))}
    )


def test_valid_assessment_passes() -> None:
    result = validate_assessment(_assessment())

    assert result.valid
    assert result.messages == ()


def test_statistics_are_deterministic() -> None:
    assessment = _assessment()

    assert calculate_statistics(assessment) == assessment.statistics


def test_noncanonical_assessment_id_is_rejected() -> None:
    assessment = _assessment(assessment_id="assessment-1")

    result = validate_assessment(assessment)

    assert not result.valid
    assert any(message.field == "assessment_id" for message in result.messages)


def test_tampered_fingerprint_is_rejected() -> None:
    assessment = _assessment().model_copy(update={"assessment_fingerprint": "f" * 64})

    result = validate_assessment(assessment)

    assert not result.valid
    assert any(message.field == "assessment_fingerprint" for message in result.messages)


def test_unknown_task_reference_is_rejected() -> None:
    assessment = _assessment(findings=(_finding(task_id="task-missing"),))

    result = validate_assessment(assessment)

    assert not result.valid
    assert any(message.field == "findings.affected_task_ids" for message in result.messages)


def test_overall_severity_mismatch_is_rejected() -> None:
    assessment = _assessment(overall_severity=ImpactSeverity.LOW)

    result = validate_assessment(assessment)

    assert not result.valid
    assert any(message.field == "overall_severity" for message in result.messages)


def test_statistics_mismatch_is_rejected() -> None:
    assessment = _assessment(
        statistics=ImpactStatistics(
            finding_count=99,
            affected_task_count=1,
            affected_component_count=0,
            high_impact_count=0,
            critical_impact_count=0,
        )
    )

    result = validate_assessment(assessment)

    assert not result.valid
    assert any(message.field == "statistics" for message in result.messages)


def test_noncanonical_finding_order_is_rejected() -> None:
    first = _finding(
        finding_id="finding-2",
        task_id="task-1",
    )
    second = _finding(
        finding_id="finding-1",
        task_id="task-1",
    )
    assessment = _assessment(
        findings=(first, second),
        statistics=ImpactStatistics(
            finding_count=2,
            affected_task_count=1,
            affected_component_count=0,
            high_impact_count=0,
            critical_impact_count=0,
        ),
    )

    result = validate_assessment(assessment)

    assert not result.valid
    assert any(message.field == "findings" for message in result.messages)


def test_noncanonical_option_order_is_rejected() -> None:
    recommendation = DecisionRecommendation(
        recommendation_id="recommendation-1",
        selected_option_id="option-1",
        options=(
            _option("option-2"),
            _option("option-1"),
        ),
        rationale="Proceed with validation.",
        confidence=DecisionConfidence.HIGH,
        validation_requirements=(_validation(),),
    )
    assessment = _assessment(recommendation=recommendation)

    result = validate_assessment(assessment)

    assert not result.valid
    assert any(message.field == "recommendation.options" for message in result.messages)


def test_limits_are_enforced() -> None:
    assessment = _assessment()
    configuration = ImpactDecisionConfiguration(
        max_findings=1,
        max_options=1,
        max_affected_tasks=1,
        max_affected_components=1,
    )

    assert validate_assessment(
        assessment,
        configuration,
    ).valid


def test_disabled_configuration_fails_closed() -> None:
    result = validate_assessment(
        _assessment(),
        ImpactDecisionConfiguration(enabled=False),
    )

    assert not result.valid
    assert any(message.field == "configuration.enabled" for message in result.messages)


def test_high_impact_with_approval_passes() -> None:
    finding = _finding(severity=ImpactSeverity.HIGH)
    recommendation = DecisionRecommendation(
        recommendation_id="recommendation-1",
        selected_option_id="option-1",
        options=(_option(),),
        rationale="Proceed after approval.",
        confidence=DecisionConfidence.HIGH,
        approval_requirements=(_approval(),),
        validation_requirements=(_validation(),),
    )
    assessment = _assessment(
        findings=(finding,),
        recommendation=recommendation,
        overall_severity=ImpactSeverity.HIGH,
        statistics=ImpactStatistics(
            finding_count=1,
            affected_task_count=1,
            affected_component_count=0,
            high_impact_count=1,
            critical_impact_count=0,
        ),
    )

    assert validate_assessment(assessment).valid
