"""Impact Decision domain-model tests."""

from typing import Any

import pytest
from pydantic import ValidationError

from forge.impact.models import (
    SCHEMA_VERSION,
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
    ImpactDecisionGeneration,
    ImpactDecisionStore,
    ImpactFinding,
    ImpactScope,
    ImpactSeverity,
    ImpactStatistics,
    ImpactValidationCategory,
)


def _option(
    option_id: str = "option-proceed",
) -> DecisionOption:
    return DecisionOption(
        option_id=option_id,
        title="Proceed",
        description="Proceed with controlled validation.",
        decision_type=DecisionType.PROCEED,
    )


def _validation() -> DecisionValidationRequirement:
    return DecisionValidationRequirement(
        requirement_id="validation-1",
        category=ImpactValidationCategory.UNIT_TESTING,
        description="Relevant unit tests must pass.",
    )


def _approval() -> DecisionApprovalRequirement:
    return DecisionApprovalRequirement(
        requirement_id="approval-1",
        level=ImpactApprovalLevel.HIGH_RISK_APPROVAL,
        reason="High-impact change requires review.",
    )


def _recommendation(
    *,
    approvals: tuple[
        DecisionApprovalRequirement,
        ...,
    ] = (),
    validations: tuple[
        DecisionValidationRequirement,
        ...,
    ]
    | None = None,
) -> DecisionRecommendation:
    return DecisionRecommendation(
        recommendation_id="recommendation-1",
        selected_option_id="option-proceed",
        options=(_option(),),
        rationale="The controlled option has acceptable residual risk.",
        confidence=DecisionConfidence.HIGH,
        approval_requirements=approvals,
        validation_requirements=((_validation(),) if validations is None else validations),
    )


def _finding(
    severity: ImpactSeverity = ImpactSeverity.MEDIUM,
) -> ImpactFinding:
    return ImpactFinding(
        finding_id="finding-1",
        category=ImpactCategory.ARCHITECTURE,
        scope=ImpactScope.TASK,
        severity=severity,
        summary="Task contract is affected.",
        rationale="The proposed change modifies task behavior.",
        affected_task_ids=("task-1",),
    )


def _statistics(
    *,
    high: int = 0,
    critical: int = 0,
) -> ImpactStatistics:
    return ImpactStatistics(
        finding_count=1,
        affected_task_count=1,
        affected_component_count=0,
        high_impact_count=high,
        critical_impact_count=critical,
    )


def _assessment(**updates: Any) -> ImpactAssessment:
    values: dict[str, Any] = {
        "assessment_id": "impact-00000000000000000001",
        "assessment_fingerprint": "a" * 64,
        "mission_id": "mission-1",
        "task_set_fingerprint": "b" * 64,
        "task_ids": ("task-1",),
        "findings": (_finding(),),
        "recommendation": _recommendation(),
        "status": DecisionStatus.READY,
        "confidence": DecisionConfidence.HIGH,
        "overall_severity": ImpactSeverity.MEDIUM,
        "statistics": _statistics(),
    }
    values.update(updates)
    return ImpactAssessment(**values)


def test_schema_version_is_frozen() -> None:
    assert SCHEMA_VERSION == "1.0"


def test_configuration_defaults_are_safe() -> None:
    configuration = ImpactDecisionConfiguration()

    assert configuration.enabled
    assert not configuration.strict
    assert configuration.history_limit == 5
    assert configuration.max_findings == 250


def test_models_are_immutable() -> None:
    assessment = _assessment()

    with pytest.raises(ValidationError):
        assessment.mission_id = "changed"


def test_unknown_fields_are_rejected() -> None:
    payload = _assessment().model_dump()
    payload["unexpected"] = True

    with pytest.raises(ValidationError):
        ImpactAssessment.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "assessment_id",
        "assessment_fingerprint",
        "mission_id",
        "task_set_fingerprint",
    ],
)
def test_blank_assessment_identity_is_rejected(
    field: str,
) -> None:
    with pytest.raises(ValidationError):
        _assessment(**{field: "   "})


def test_finding_requires_affected_target() -> None:
    with pytest.raises(ValidationError):
        ImpactFinding(
            finding_id="finding-1",
            category=ImpactCategory.UNKNOWN,
            scope=ImpactScope.UNKNOWN,
            severity=ImpactSeverity.LOW,
            summary="Unknown impact.",
            rationale="No controlled affected target exists.",
        )


def test_finding_accepts_controlled_scope() -> None:
    finding = ImpactFinding(
        finding_id="finding-1",
        category=ImpactCategory.CONFIGURATION,
        scope=ImpactScope.CONFIGURATION,
        severity=ImpactSeverity.LOW,
        summary="Configuration may change.",
        rationale="A controlled configuration scope is affected.",
    )

    assert finding.scope is ImpactScope.CONFIGURATION


def test_empty_findings_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _assessment(findings=())


def test_recommendation_requires_options() -> None:
    with pytest.raises(ValidationError):
        DecisionRecommendation(
            recommendation_id="recommendation-1",
            selected_option_id="option-1",
            options=(),
            rationale="No options exist.",
            confidence=DecisionConfidence.LOW,
            validation_requirements=(_validation(),),
        )


def test_selected_option_must_exist() -> None:
    with pytest.raises(ValidationError):
        DecisionRecommendation(
            recommendation_id="recommendation-1",
            selected_option_id="missing",
            options=(_option(),),
            rationale="Selected option is invalid.",
            confidence=DecisionConfidence.LOW,
            validation_requirements=(_validation(),),
        )


def test_duplicate_option_ids_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DecisionRecommendation(
            recommendation_id="recommendation-1",
            selected_option_id="option-proceed",
            options=(_option(), _option()),
            rationale="Duplicate options are invalid.",
            confidence=DecisionConfidence.LOW,
            validation_requirements=(_validation(),),
        )


def test_validation_obligations_are_required() -> None:
    with pytest.raises(ValidationError):
        _recommendation(validations=())


def test_blocked_decision_requires_reason() -> None:
    with pytest.raises(ValidationError):
        _assessment(
            status=DecisionStatus.BLOCKED,
            blocking_reason=None,
        )


def test_blocked_decision_accepts_reason() -> None:
    assessment = _assessment(
        status=DecisionStatus.BLOCKED,
        blocking_reason="Required architecture evidence is missing.",
    )

    assert assessment.blocking_reason is not None


def test_non_blocked_decision_rejects_reason() -> None:
    with pytest.raises(ValidationError):
        _assessment(
            status=DecisionStatus.READY,
            blocking_reason="Incorrect state.",
        )


@pytest.mark.parametrize(
    "severity",
    [
        ImpactSeverity.HIGH,
        ImpactSeverity.CRITICAL,
    ],
)
def test_high_impact_requires_approval(
    severity: ImpactSeverity,
) -> None:
    with pytest.raises(ValidationError):
        _assessment(
            findings=(_finding(severity),),
            overall_severity=severity,
            statistics=_statistics(
                high=int(severity is ImpactSeverity.HIGH),
                critical=int(severity is ImpactSeverity.CRITICAL),
            ),
        )


def test_high_impact_accepts_approval() -> None:
    assessment = _assessment(
        findings=(_finding(ImpactSeverity.HIGH),),
        overall_severity=ImpactSeverity.HIGH,
        statistics=_statistics(high=1),
        recommendation=_recommendation(
            approvals=(_approval(),),
        ),
    )

    assert assessment.overall_severity is ImpactSeverity.HIGH


def test_task_ids_are_normalized() -> None:
    assessment = _assessment(
        task_ids=("task-2", "task-1", "task-2", " "),
    )

    assert assessment.task_ids == ("task-1", "task-2")


def test_store_defaults_are_empty() -> None:
    store = ImpactDecisionStore()

    assert store.schema_version == SCHEMA_VERSION
    assert store.assessments == {}
    assert store.history == {}
    assert store.generations == {}


def test_store_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ImpactDecisionStore.model_validate(
            {
                "schema_version": SCHEMA_VERSION,
                "unexpected": True,
            }
        )


def test_generation_rejects_blank_identity() -> None:
    with pytest.raises(ValidationError):
        ImpactDecisionGeneration(
            generation_id=" ",
            assessment_id="assessment-1",
            assessment_fingerprint="a" * 64,
            mission_id="mission-1",
            task_set_fingerprint="b" * 64,
            finding_count=1,
        )


def test_serialization_is_deterministic() -> None:
    first = _assessment()
    second = _assessment()

    assert first.model_dump_json() == second.model_dump_json()


def test_round_trip_serialization() -> None:
    assessment = _assessment()
    restored = ImpactAssessment.model_validate_json(assessment.model_dump_json())

    assert restored == assessment
