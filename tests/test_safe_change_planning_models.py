"""Safe Change Planning model tests."""

from types import MappingProxyType

import pytest
from pydantic import ValidationError

from forge.safe_change_planning.models import (
    ChangeAction,
    ChangeActionType,
    ChangePhase,
    ChangeRequest,
    ChangeRiskAssessment,
    ChangeTarget,
    ChangeTargetType,
    DependencyImpact,
    DependencyType,
    FindingSeverity,
    PlanningPhaseType,
    PlanningValidationFinding,
    PlanningValidationResult,
    PlanStatistics,
    RiskFactor,
    RiskFactorType,
    RiskLevel,
    RollbackStep,
    SafeChangePlan,
    VerificationStep,
    VerificationType,
)


def _request() -> ChangeRequest:
    return ChangeRequest(
        request_id="change-request-123",
        request_fingerprint="a" * 64,
        mission_id="mission-123",
        task_ids=("task-b", "task-a"),
        objective="Implement safe change planning",
        constraints=("No mutation",),
        requested_outcomes=("Deterministic plan",),
        source_fingerprints={
            "mission": "b" * 64,
            "tasks": "c" * 64,
        },
    )


def _target() -> ChangeTarget:
    return ChangeTarget(
        target_id="target-1",
        target_type=ChangeTargetType.FILE,
        path="forge/example.py",
        component="example",
        reason="Implementation target",
        source_ids=("task-a",),
    )


def _verification() -> VerificationStep:
    return VerificationStep(
        step_id="verification-1",
        verification_type=VerificationType.UNIT_TEST,
        description="Run unit tests",
        target_ids=("target-1",),
        command="python -m pytest",
    )


def _rollback() -> RollbackStep:
    return RollbackStep(
        step_id="rollback-1",
        description="Restore previous file",
        target_ids=("target-1",),
    )


def _action() -> ChangeAction:
    return ChangeAction(
        action_id="action-1",
        target_id="target-1",
        action_type=ChangeActionType.MODIFY,
        description="Modify implementation",
        verification_step_ids=("verification-1",),
        rollback_step_ids=("rollback-1",),
    )


def _risk() -> ChangeRiskAssessment:
    return ChangeRiskAssessment(
        assessment_id="risk-1",
        risk_level=RiskLevel.MEDIUM,
        score=45,
        factors=(),
        approval_required=True,
        mitigations=("Run regression tests",),
    )


def _phase() -> ChangePhase:
    return ChangePhase(
        phase_id="phase-1",
        phase_type=PlanningPhaseType.IMPLEMENTATION,
        sequence=1,
        title="Implementation",
        action_ids=("action-1",),
    )


def _plan() -> SafeChangePlan:
    return SafeChangePlan(
        plan_id="safe-change-plan-1",
        plan_fingerprint="d" * 64,
        request=_request(),
        targets=(_target(),),
        actions=(_action(),),
        dependencies=(),
        risk_assessment=_risk(),
        verification_steps=(_verification(),),
        rollback_steps=(_rollback(),),
        phases=(_phase(),),
        statistics=PlanStatistics(
            target_count=1,
            action_count=1,
            dependency_count=0,
            verification_count=1,
            rollback_count=1,
            phase_count=1,
            high_risk_factor_count=0,
        ),
        source_fingerprints={
            "mission": "b" * 64,
            "tasks": "c" * 64,
        },
    )


def test_request_normalizes_sequences() -> None:
    request = ChangeRequest(
        request_id="request",
        request_fingerprint="fingerprint",
        mission_id="mission",
        task_ids=("task-b", "task-a", "task-a", " "),
        objective=" Objective ",
        constraints=(" constraint-b ", "constraint-a"),
        requested_outcomes=("outcome-b", "outcome-a"),
    )

    assert request.task_ids == ("task-a", "task-b")
    assert request.constraints == (
        "constraint-a",
        "constraint-b",
    )
    assert request.requested_outcomes == (
        "outcome-a",
        "outcome-b",
    )
    assert request.objective == "Objective"


def test_request_rejects_blank_identity() -> None:
    with pytest.raises(ValidationError):
        ChangeRequest(
            request_id=" ",
            request_fingerprint="fingerprint",
            mission_id="mission",
            task_ids=("task-a",),
            objective="Objective",
        )


def test_request_mapping_is_immutable() -> None:
    request = _request()

    assert isinstance(
        request.source_fingerprints,
        MappingProxyType,
    )

    with pytest.raises(TypeError):
        request.source_fingerprints["new"] = "value"  # type: ignore[index]


def test_request_serializes_mapping_canonically() -> None:
    request = ChangeRequest(
        request_id="request",
        request_fingerprint="fingerprint",
        mission_id="mission",
        task_ids=("task-a",),
        objective="Objective",
        source_fingerprints={
            "z": "2",
            "a": "1",
        },
    )

    payload = request.model_dump(mode="json")

    assert list(payload["source_fingerprints"]) == [
        "a",
        "z",
    ]


def test_target_normalizes_source_ids() -> None:
    target = ChangeTarget(
        target_id="target",
        target_type=ChangeTargetType.FILE,
        path=" file.py ",
        component=" component ",
        reason=" reason ",
        source_ids=("task-b", "task-a", "task-a"),
    )

    assert target.path == "file.py"
    assert target.component == "component"
    assert target.reason == "reason"
    assert target.source_ids == ("task-a", "task-b")


def test_target_metadata_is_immutable() -> None:
    target = ChangeTarget(
        target_id="target",
        target_type=ChangeTargetType.FILE,
        path="file.py",
        component="component",
        reason="reason",
        metadata={"z": "2", "a": "1"},
    )

    assert isinstance(target.metadata, MappingProxyType)
    assert list(target.model_dump(mode="json")["metadata"]) == [
        "a",
        "z",
    ]


def test_action_normalizes_references() -> None:
    action = ChangeAction(
        action_id="action",
        target_id="target",
        action_type=ChangeActionType.MODIFY,
        description="Change file",
        prerequisites=("action-b", "action-a", "action-a"),
        verification_step_ids=("verify-b", "verify-a"),
        rollback_step_ids=("rollback-b", "rollback-a"),
    )

    assert action.prerequisites == (
        "action-a",
        "action-b",
    )
    assert action.verification_step_ids == (
        "verify-a",
        "verify-b",
    )
    assert action.rollback_step_ids == (
        "rollback-a",
        "rollback-b",
    )


def test_dependency_requires_positive_depth() -> None:
    with pytest.raises(ValidationError):
        DependencyImpact(
            dependency_id="dependency",
            source_target_id="target-a",
            affected_target_id="target-b",
            dependency_type=DependencyType.DIRECT,
            depth=0,
            reason="dependency",
        )


def test_risk_factor_rejects_score_above_one_hundred() -> None:
    with pytest.raises(ValidationError):
        RiskFactor(
            factor_id="factor",
            factor_type=RiskFactorType.SECURITY,
            score=101,
            reason="Security impact",
        )


def test_risk_factor_normalizes_optional_mitigation() -> None:
    factor = RiskFactor(
        factor_id="factor",
        factor_type=RiskFactorType.CONFIGURATION,
        score=20,
        reason="Configuration change",
        mitigation=" ",
    )

    assert factor.mitigation is None


def test_high_risk_requires_approval() -> None:
    with pytest.raises(ValidationError):
        ChangeRiskAssessment(
            assessment_id="risk",
            risk_level=RiskLevel.HIGH,
            score=70,
            factors=(),
            approval_required=False,
            mitigations=("Mitigation",),
        )


def test_high_risk_requires_mitigation() -> None:
    with pytest.raises(ValidationError):
        ChangeRiskAssessment(
            assessment_id="risk",
            risk_level=RiskLevel.HIGH,
            score=70,
            factors=(),
            approval_required=True,
            mitigations=(),
        )


def test_medium_risk_accepts_empty_mitigation() -> None:
    assessment = ChangeRiskAssessment(
        assessment_id="risk",
        risk_level=RiskLevel.MEDIUM,
        score=40,
        factors=(),
        approval_required=True,
        mitigations=(),
    )

    assert assessment.risk_level is RiskLevel.MEDIUM


def test_verification_normalizes_target_ids() -> None:
    step = VerificationStep(
        step_id="verify",
        verification_type=VerificationType.UNIT_TEST,
        description="Run tests",
        target_ids=("target-b", "target-a", "target-a"),
        command=" python -m pytest ",
    )

    assert step.target_ids == ("target-a", "target-b")
    assert step.command == "python -m pytest"


def test_irreversible_rollback_requires_limitation() -> None:
    with pytest.raises(ValidationError):
        RollbackStep(
            step_id="rollback",
            description="Cannot reverse",
            target_ids=("target",),
            irreversible=True,
        )


def test_irreversible_rollback_accepts_limitation() -> None:
    step = RollbackStep(
        step_id="rollback",
        description="Manual compensation",
        target_ids=("target",),
        irreversible=True,
        limitation="Data cannot be restored automatically",
    )

    assert step.irreversible is True
    assert step.limitation is not None


def test_phase_requires_positive_sequence() -> None:
    with pytest.raises(ValidationError):
        ChangePhase(
            phase_id="phase",
            phase_type=PlanningPhaseType.PREPARATION,
            sequence=0,
            title="Preparation",
            action_ids=("action",),
        )


def test_plan_accepts_consistent_contents() -> None:
    plan = _plan()

    assert plan.statistics.target_count == 1
    assert plan.statistics.action_count == 1
    assert plan.statistics.verification_count == 1


def test_plan_rejects_duplicate_targets() -> None:
    plan = _plan()

    with pytest.raises(ValidationError):
        plan.model_copy(
            update={
                "targets": (
                    plan.targets[0],
                    plan.targets[0],
                )
            }
        ).model_validate(
            plan.model_copy(
                update={
                    "targets": (
                        plan.targets[0],
                        plan.targets[0],
                    )
                }
            ).model_dump()
        )


def test_plan_rejects_unknown_action_target() -> None:
    plan = _plan()
    invalid_action = plan.actions[0].model_copy(update={"target_id": "missing-target"})

    payload = plan.model_dump()
    payload["actions"] = (invalid_action,)

    with pytest.raises(ValidationError):
        SafeChangePlan.model_validate(payload)


def test_plan_rejects_unknown_verification_reference() -> None:
    plan = _plan()
    invalid_action = plan.actions[0].model_copy(
        update={"verification_step_ids": ("missing-verification",)}
    )

    payload = plan.model_dump()
    payload["actions"] = (invalid_action,)

    with pytest.raises(ValidationError):
        SafeChangePlan.model_validate(payload)


def test_plan_rejects_unknown_rollback_reference() -> None:
    plan = _plan()
    invalid_action = plan.actions[0].model_copy(update={"rollback_step_ids": ("missing-rollback",)})

    payload = plan.model_dump()
    payload["actions"] = (invalid_action,)

    with pytest.raises(ValidationError):
        SafeChangePlan.model_validate(payload)


def test_plan_rejects_unknown_phase_action() -> None:
    plan = _plan()
    invalid_phase = plan.phases[0].model_copy(update={"action_ids": ("missing-action",)})

    payload = plan.model_dump()
    payload["phases"] = (invalid_phase,)

    with pytest.raises(ValidationError):
        SafeChangePlan.model_validate(payload)


def test_plan_rejects_statistics_mismatch() -> None:
    plan = _plan()

    payload = plan.model_dump()
    payload["statistics"] = PlanStatistics(
        target_count=99,
        action_count=1,
        dependency_count=0,
        verification_count=1,
        rollback_count=1,
        phase_count=1,
        high_risk_factor_count=0,
    )

    with pytest.raises(ValidationError):
        SafeChangePlan.model_validate(payload)


def test_valid_result_accepts_no_errors() -> None:
    result = PlanningValidationResult(
        valid=True,
        findings=(
            PlanningValidationFinding(
                code="warning",
                message="Warning only",
                severity=FindingSeverity.WARNING,
            ),
        ),
    )

    assert result.valid is True


def test_valid_result_rejects_error_finding() -> None:
    with pytest.raises(ValidationError):
        PlanningValidationResult(
            valid=True,
            findings=(
                PlanningValidationFinding(
                    code="error",
                    message="Invalid",
                    severity=FindingSeverity.ERROR,
                ),
            ),
        )


def test_invalid_result_requires_error_finding() -> None:
    with pytest.raises(ValidationError):
        PlanningValidationResult(
            valid=False,
            findings=(
                PlanningValidationFinding(
                    code="warning",
                    message="Warning only",
                    severity=FindingSeverity.WARNING,
                ),
            ),
        )


def test_models_are_frozen() -> None:
    request = _request()

    with pytest.raises(ValidationError):
        request.mission_id = "different"
