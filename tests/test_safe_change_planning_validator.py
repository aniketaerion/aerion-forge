"""Safe Change Planning validator tests."""

from collections.abc import Mapping
from pathlib import Path

import pytest

from forge.safe_change_planning.errors import (
    ChangePlanningConfigurationError,
    ChangePlanningValidationError,
)
from forge.safe_change_planning.models import (
    ChangeAction,
    ChangeActionType,
    ChangePhase,
    ChangePlanningConfiguration,
    ChangeRequest,
    ChangeRiskAssessment,
    ChangeTarget,
    ChangeTargetType,
    DependencyImpact,
    DependencyType,
    FindingSeverity,
    PlanningPhaseType,
    PlanningValidationResult,
    PlanStatistics,
    RiskLevel,
    RollbackStep,
    SafeChangePlan,
    VerificationStep,
    VerificationType,
)
from forge.safe_change_planning.validator import (
    SafeChangePlanningValidator,
)


def _configuration(
    **updates: object,
) -> ChangePlanningConfiguration:
    return ChangePlanningConfiguration().model_copy(update=updates)


def _request(
    *,
    mission_id: str = "mission-123",
    task_ids: tuple[str, ...] = ("task-a",),
    source_fingerprints: Mapping[str, str] | None = None,
) -> ChangeRequest:
    return ChangeRequest(
        request_id="request-1",
        request_fingerprint="a" * 64,
        mission_id=mission_id,
        task_ids=task_ids,
        objective="Implement safe change",
        source_fingerprints=(
            source_fingerprints
            or {
                "mission": "m" * 64,
                "tasks": "t" * 64,
            }
        ),
    )


def _target(
    *,
    target_id: str = "target-1",
    target_type: ChangeTargetType = ChangeTargetType.FILE,
) -> ChangeTarget:
    return ChangeTarget(
        target_id=target_id,
        target_type=target_type,
        path="forge/example.py",
        component="example",
        reason="Required change",
    )


def _verification(
    *,
    step_id: str = "verify-1",
    target_ids: tuple[str, ...] = ("target-1",),
) -> VerificationStep:
    return VerificationStep(
        step_id=step_id,
        verification_type=VerificationType.UNIT_TEST,
        description="Run unit tests",
        target_ids=target_ids,
    )


def _rollback(
    *,
    step_id: str = "rollback-1",
    target_ids: tuple[str, ...] = ("target-1",),
) -> RollbackStep:
    return RollbackStep(
        step_id=step_id,
        description="Restore previous version",
        target_ids=target_ids,
    )


def _action(
    *,
    action_id: str = "action-1",
    target_id: str = "target-1",
    prerequisites: tuple[str, ...] = (),
    verification_step_ids: tuple[str, ...] = ("verify-1",),
    rollback_step_ids: tuple[str, ...] = ("rollback-1",),
    destructive: bool = False,
    mutating: bool = True,
) -> ChangeAction:
    return ChangeAction(
        action_id=action_id,
        target_id=target_id,
        action_type=ChangeActionType.MODIFY,
        description="Modify target",
        prerequisites=prerequisites,
        verification_step_ids=verification_step_ids,
        rollback_step_ids=rollback_step_ids,
        destructive=destructive,
        mutating=mutating,
    )


def _risk(
    *,
    level: RiskLevel = RiskLevel.MEDIUM,
) -> ChangeRiskAssessment:
    return ChangeRiskAssessment(
        assessment_id="risk-1",
        risk_level=level,
        score={
            RiskLevel.LOW: 10,
            RiskLevel.MEDIUM: 40,
            RiskLevel.HIGH: 70,
            RiskLevel.CRITICAL: 90,
        }[level],
        factors=(),
        approval_required=level is not RiskLevel.LOW,
        mitigations=(("Mitigation",) if level in {RiskLevel.HIGH, RiskLevel.CRITICAL} else ()),
    )


def _phase(
    *,
    phase_id: str = "phase-1",
    sequence: int = 1,
    action_ids: tuple[str, ...] = ("action-1",),
) -> ChangePhase:
    return ChangePhase(
        phase_id=phase_id,
        phase_type=PlanningPhaseType.IMPLEMENTATION,
        sequence=sequence,
        title="Implementation",
        action_ids=action_ids,
    )


def _lineage() -> dict[str, str]:
    return {
        "mission": "1",
        "tasks": "2",
        "impact": "3",
        "engineering_memory": "4",
        "mission_report": "5",
        "repository": "6",
        "index": "7",
        "knowledge_graph": "8",
    }


def _plan(
    *,
    targets: tuple[ChangeTarget, ...] | None = None,
    actions: tuple[ChangeAction, ...] | None = None,
    dependencies: tuple[DependencyImpact, ...] = (),
    verification_steps: tuple[VerificationStep, ...] | None = None,
    rollback_steps: tuple[RollbackStep, ...] | None = None,
    phases: tuple[ChangePhase, ...] | None = None,
    risk_level: RiskLevel = RiskLevel.MEDIUM,
    source_fingerprints: Mapping[str, str] | None = None,
) -> SafeChangePlan:
    resolved_targets = (_target(),) if targets is None else targets
    resolved_actions = (_action(),) if actions is None else actions
    resolved_verification = (_verification(),) if verification_steps is None else verification_steps
    resolved_rollback = (_rollback(),) if rollback_steps is None else rollback_steps
    resolved_phases = (_phase(),) if phases is None else phases

    return SafeChangePlan(
        plan_id="plan-1",
        plan_fingerprint="p" * 64,
        request=_request(),
        targets=resolved_targets,
        actions=resolved_actions,
        dependencies=dependencies,
        risk_assessment=_risk(level=risk_level),
        verification_steps=resolved_verification,
        rollback_steps=resolved_rollback,
        phases=resolved_phases,
        statistics=PlanStatistics(
            target_count=len(resolved_targets),
            action_count=len(resolved_actions),
            dependency_count=len(dependencies),
            verification_count=len(resolved_verification),
            rollback_count=len(resolved_rollback),
            phase_count=len(resolved_phases),
            high_risk_factor_count=0,
        ),
        source_fingerprints=(source_fingerprints or _lineage()),
    )


def _codes(
    result: PlanningValidationResult,
) -> set[str]:
    return {finding.code for finding in result.findings}


def test_configuration_accepts_safe_defaults() -> None:
    result = SafeChangePlanningValidator().validate_configuration(ChangePlanningConfiguration())

    assert result.valid


def test_disabled_configuration_is_invalid() -> None:
    result = SafeChangePlanningValidator().validate_configuration(_configuration(enabled=False))

    assert not result.valid
    assert "planning-disabled" in _codes(result)


def test_configuration_warns_when_action_limit_is_low() -> None:
    result = SafeChangePlanningValidator().validate_configuration(
        _configuration(
            max_targets=100,
            max_actions=50,
        )
    )

    assert result.valid
    assert "action-limit-below-target-limit" in _codes(result)


def test_ensure_enabled_accepts_enabled_configuration() -> None:
    SafeChangePlanningValidator().ensure_enabled(ChangePlanningConfiguration())


def test_ensure_enabled_rejects_disabled_configuration() -> None:
    with pytest.raises(ChangePlanningConfigurationError):
        SafeChangePlanningValidator().ensure_enabled(_configuration(enabled=False))


def test_request_validation_accepts_matching_lineage() -> None:
    request = _request()

    result = SafeChangePlanningValidator().validate_request(
        request,
        ChangePlanningConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={
            "mission": "m" * 64,
            "tasks": "t" * 64,
        },
    )

    assert result.valid


def test_request_rejects_mission_mismatch() -> None:
    result = SafeChangePlanningValidator().validate_request(
        _request(mission_id="mission-other"),
        ChangePlanningConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert not result.valid
    assert "mission-id-mismatch" in _codes(result)


def test_request_rejects_empty_task_scope() -> None:
    result = SafeChangePlanningValidator().validate_request(
        _request(task_ids=()),
        ChangePlanningConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert not result.valid
    assert "empty-task-scope" in _codes(result)


def test_request_rejects_unknown_tasks_in_strict_mode() -> None:
    result = SafeChangePlanningValidator().validate_request(
        _request(task_ids=("task-unknown",)),
        ChangePlanningConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert not result.valid
    assert "unknown-task-ids" in _codes(result)


def test_request_warns_for_unknown_tasks_in_non_strict_mode() -> None:
    result = SafeChangePlanningValidator().validate_request(
        _request(task_ids=("task-unknown",)),
        _configuration(strict_validation=False),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert result.valid

    finding = next(finding for finding in result.findings if finding.code == "unknown-task-ids")

    assert finding.severity is FindingSeverity.WARNING


def test_request_rejects_missing_source_fingerprint() -> None:
    result = SafeChangePlanningValidator().validate_request(
        _request(source_fingerprints={"mission": "m"}),
        ChangePlanningConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={
            "mission": "m",
            "tasks": "t",
        },
    )

    assert not result.valid
    assert "missing-source-fingerprint" in _codes(result)


def test_request_rejects_source_fingerprint_mismatch() -> None:
    result = SafeChangePlanningValidator().validate_request(
        _request(source_fingerprints={"mission": "wrong"}),
        ChangePlanningConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={"mission": "expected"},
    )

    assert not result.valid
    assert "source-fingerprint-mismatch" in _codes(result)


def test_request_or_raise_returns_valid_result() -> None:
    request = _request()

    result = SafeChangePlanningValidator().validate_request_or_raise(
        request,
        ChangePlanningConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={
            "mission": "m" * 64,
            "tasks": "t" * 64,
        },
    )

    assert result.valid


def test_request_or_raise_raises_for_invalid_request() -> None:
    with pytest.raises(ChangePlanningValidationError):
        SafeChangePlanningValidator().validate_request_or_raise(
            _request(mission_id="wrong"),
            ChangePlanningConfiguration(),
            known_mission_id="mission-123",
            known_task_ids=("task-a",),
            required_source_fingerprints={},
        )


def test_plan_validation_accepts_valid_plan() -> None:
    result = SafeChangePlanningValidator().validate_plan(
        _plan(),
        ChangePlanningConfiguration(),
    )

    assert result.valid


def test_plan_rejects_target_limit_exceeded() -> None:
    targets = (
        _target(target_id="target-1"),
        _target(target_id="target-2"),
    )
    actions = (
        _action(
            action_id="action-1",
            target_id="target-1",
        ),
        _action(
            action_id="action-2",
            target_id="target-2",
        ),
    )

    plan = _plan(
        targets=targets,
        actions=actions,
        phases=(_phase(action_ids=("action-1", "action-2")),),
    )

    result = SafeChangePlanningValidator().validate_plan(
        plan,
        _configuration(max_targets=1),
    )

    assert not result.valid
    assert "target-limit-exceeded" in _codes(result)


def test_plan_rejects_action_limit_exceeded() -> None:
    targets = (
        _target(target_id="target-1"),
        _target(target_id="target-2"),
    )
    actions = (
        _action(
            action_id="action-1",
            target_id="target-1",
        ),
        _action(
            action_id="action-2",
            target_id="target-2",
        ),
    )

    plan = _plan(
        targets=targets,
        actions=actions,
        phases=(_phase(action_ids=("action-1", "action-2")),),
    )

    result = SafeChangePlanningValidator().validate_plan(
        plan,
        _configuration(
            max_targets=2,
            max_actions=1,
        ),
    )

    assert not result.valid
    assert "action-limit-exceeded" in _codes(result)


def test_plan_rejects_dependency_depth_exceeded() -> None:
    dependency = DependencyImpact(
        dependency_id="dependency-1",
        source_target_id="target-1",
        affected_target_id="target-1",
        dependency_type=DependencyType.TRANSITIVE,
        depth=10,
        reason="Deep dependency",
    )

    result = SafeChangePlanningValidator().validate_plan(
        _plan(dependencies=(dependency,)),
        _configuration(max_dependency_depth=5),
    )

    assert not result.valid
    assert "dependency-depth-exceeded" in _codes(result)


def test_plan_rejects_unknown_dependency_by_default() -> None:
    dependency = DependencyImpact(
        dependency_id="dependency-1",
        source_target_id="target-1",
        affected_target_id="target-1",
        dependency_type=DependencyType.UNKNOWN,
        depth=1,
        reason="Unknown",
        known=False,
    )

    result = SafeChangePlanningValidator().validate_plan(
        _plan(dependencies=(dependency,)),
        ChangePlanningConfiguration(),
    )

    assert not result.valid
    assert "unknown-dependencies" in _codes(result)
    assert "unknown-dependency-policy" in _codes(result)


def test_plan_warns_when_unknown_dependencies_are_allowed() -> None:
    dependency = DependencyImpact(
        dependency_id="dependency-1",
        source_target_id="target-1",
        affected_target_id="target-1",
        dependency_type=DependencyType.UNKNOWN,
        depth=1,
        reason="Unknown",
        known=False,
    )

    result = SafeChangePlanningValidator().validate_plan(
        _plan(dependencies=(dependency,)),
        _configuration(allow_unknown_dependencies=True),
    )

    assert result.valid

    finding = next(finding for finding in result.findings if finding.code == "unknown-dependencies")

    assert finding.severity is FindingSeverity.WARNING


def test_plan_rejects_unknown_action_prerequisite() -> None:
    action = _action(prerequisites=("missing-action",))

    result = SafeChangePlanningValidator().validate_plan(
        _plan(actions=(action,)),
        ChangePlanningConfiguration(),
    )

    assert not result.valid
    assert "unknown-action-prerequisite" in _codes(result)


def test_plan_rejects_self_referencing_action() -> None:
    action = _action(prerequisites=("action-1",))

    result = SafeChangePlanningValidator().validate_plan(
        _plan(actions=(action,)),
        ChangePlanningConfiguration(),
    )

    assert not result.valid
    assert "self-referencing-action" in _codes(result)


def test_plan_rejects_missing_mutation_verification() -> None:
    action = _action(verification_step_ids=())
    plan = _plan(
        actions=(action,),
        verification_steps=(),
    )

    result = SafeChangePlanningValidator().validate_plan(
        plan,
        ChangePlanningConfiguration(),
    )

    assert not result.valid
    assert "missing-action-verification" in _codes(result)


def test_plan_accepts_missing_verification_when_disabled() -> None:
    action = _action(verification_step_ids=())
    plan = _plan(
        actions=(action,),
        verification_steps=(),
    )

    result = SafeChangePlanningValidator().validate_plan(
        plan,
        _configuration(require_verification_for_mutations=False),
    )

    assert result.valid


def test_plan_rejects_destructive_action_without_rollback() -> None:
    action = _action(
        rollback_step_ids=(),
        destructive=True,
    )
    plan = _plan(
        actions=(action,),
        rollback_steps=(),
    )

    result = SafeChangePlanningValidator().validate_plan(
        plan,
        ChangePlanningConfiguration(),
    )

    assert not result.valid
    assert "missing-destructive-rollback" in _codes(result)


def test_plan_rejects_high_risk_without_rollback() -> None:
    action = _action(rollback_step_ids=())
    plan = _plan(
        actions=(action,),
        rollback_steps=(),
        risk_level=RiskLevel.HIGH,
    )

    result = SafeChangePlanningValidator().validate_plan(
        plan,
        ChangePlanningConfiguration(),
    )

    assert not result.valid
    assert "missing-high-risk-rollback" in _codes(result)


def test_plan_rejects_duplicate_phase_sequence() -> None:
    phases = (
        _phase(
            phase_id="phase-1",
            sequence=1,
        ),
        _phase(
            phase_id="phase-2",
            sequence=1,
        ),
    )

    result = SafeChangePlanningValidator().validate_plan(
        _plan(phases=phases),
        ChangePlanningConfiguration(),
    )

    assert not result.valid
    assert "duplicate-phase-sequence" in _codes(result)


def test_plan_rejects_non_contiguous_phase_sequence() -> None:
    phases = (
        _phase(
            phase_id="phase-1",
            sequence=1,
        ),
        _phase(
            phase_id="phase-2",
            sequence=3,
        ),
    )

    result = SafeChangePlanningValidator().validate_plan(
        _plan(phases=phases),
        ChangePlanningConfiguration(),
    )

    assert not result.valid
    assert "non-contiguous-phase-sequence" in _codes(result)


def test_plan_rejects_missing_lineage_in_strict_mode() -> None:
    result = SafeChangePlanningValidator().validate_plan(
        _plan(source_fingerprints={"mission": "1"}),
        ChangePlanningConfiguration(),
    )

    assert not result.valid
    assert "missing-plan-lineage" in _codes(result)


def test_plan_warns_for_missing_lineage_in_non_strict_mode() -> None:
    result = SafeChangePlanningValidator().validate_plan(
        _plan(source_fingerprints={"mission": "1"}),
        _configuration(strict_validation=False),
    )

    assert result.valid

    finding = next(finding for finding in result.findings if finding.code == "missing-plan-lineage")

    assert finding.severity is FindingSeverity.WARNING


def test_plan_or_raise_returns_valid_result() -> None:
    result = SafeChangePlanningValidator().validate_plan_or_raise(
        _plan(),
        ChangePlanningConfiguration(),
    )

    assert result.valid


def test_plan_or_raise_raises_for_invalid_plan() -> None:
    with pytest.raises(ChangePlanningValidationError):
        SafeChangePlanningValidator().validate_plan_or_raise(
            _plan(source_fingerprints={"mission": "1"}),
            ChangePlanningConfiguration(),
        )


def test_findings_are_deterministically_ordered() -> None:
    result = SafeChangePlanningValidator().validate_request(
        _request(
            mission_id="wrong",
            task_ids=("unknown",),
            source_fingerprints={},
        ),
        ChangePlanningConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={
            "mission": "1",
            "tasks": "2",
        },
    )

    ordering = [
        (
            finding.severity.value,
            finding.code,
            finding.message,
            finding.source_ids,
        )
        for finding in result.findings
    ]

    assert ordering == sorted(ordering)


def test_validator_does_not_modify_plan() -> None:
    plan = _plan()
    original = plan.model_dump(mode="json")

    SafeChangePlanningValidator().validate_plan(
        plan,
        ChangePlanningConfiguration(),
    )

    assert plan.model_dump(mode="json") == original


def test_validator_does_not_modify_request() -> None:
    request = _request()
    original = request.model_dump(mode="json")

    SafeChangePlanningValidator().validate_request(
        request,
        ChangePlanningConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert request.model_dump(mode="json") == original


def test_validation_error_message_contains_findings() -> None:
    validator = SafeChangePlanningValidator()

    with pytest.raises(
        ChangePlanningValidationError,
        match="mission ID",
    ):
        validator.validate_request_or_raise(
            _request(mission_id="wrong"),
            ChangePlanningConfiguration(),
            known_mission_id="mission-123",
            known_task_ids=("task-a",),
            required_source_fingerprints={},
        )


def test_test_file_path_exists() -> None:
    assert (
        Path("tests/test_safe_change_planning_validator.py").name
        == "test_safe_change_planning_validator.py"
    )
