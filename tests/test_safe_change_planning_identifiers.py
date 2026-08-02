"""Safe Change Planning identifier and policy tests."""

import pytest

from forge.safe_change_planning.errors import (
    ChangePlanningRiskError,
)
from forge.safe_change_planning.identifiers import (
    change_action_fingerprint,
    change_action_id,
    change_phase_id,
    change_request_fingerprint,
    change_request_id,
    change_target_fingerprint,
    change_target_id,
    dependency_impact_fingerprint,
    dependency_impact_id,
    risk_assessment_id,
    risk_factor_id,
    rollback_step_id,
    safe_change_plan_fingerprint,
    safe_change_plan_id,
    verification_step_id,
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
    PlanningPhaseType,
    PlanStatistics,
    RiskFactor,
    RiskFactorType,
    RiskLevel,
    RollbackStep,
    SafeChangePlan,
    VerificationStep,
    VerificationType,
)
from forge.safe_change_planning.policies import (
    aggregate_risk_score,
    approval_required,
    build_risk_assessment,
    destructive_action_present,
    enforce_risk_controls,
    enforce_unknown_dependency_policy,
    maximum_dependency_depth,
    mutating_action_count,
    requires_rollback,
    requires_verification,
    risk_level_for_score,
    unknown_dependency_present,
)


def _request() -> ChangeRequest:
    request_id = change_request_id(
        mission_id="mission-123",
        task_ids=("task-b", "task-a"),
        objective="Implement change",
        constraints=("No mutation",),
        requested_outcomes=("Safe plan",),
        source_fingerprints={
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )

    provisional = ChangeRequest(
        request_id=request_id,
        request_fingerprint="pending",
        mission_id="mission-123",
        task_ids=("task-b", "task-a"),
        objective="Implement change",
        constraints=("No mutation",),
        requested_outcomes=("Safe plan",),
        source_fingerprints={
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )

    return provisional.model_copy(
        update={"request_fingerprint": (change_request_fingerprint(provisional))}
    )


def _target(
    *,
    target_type: ChangeTargetType = ChangeTargetType.FILE,
    path: str = "forge/example.py",
    component: str = "example",
) -> ChangeTarget:
    return ChangeTarget(
        target_id=change_target_id(
            target_type=target_type.value,
            path=path,
            component=component,
        ),
        target_type=target_type,
        path=path,
        component=component,
        reason="Required change",
    )


def _verification(
    target: ChangeTarget,
) -> VerificationStep:
    return VerificationStep(
        step_id=verification_step_id(
            request_id=_request().request_id,
            verification_type=VerificationType.UNIT_TEST.value,
            description="Run unit tests",
            target_ids=(target.target_id,),
        ),
        verification_type=VerificationType.UNIT_TEST,
        description="Run unit tests",
        target_ids=(target.target_id,),
    )


def _rollback(
    target: ChangeTarget,
) -> RollbackStep:
    return RollbackStep(
        step_id=rollback_step_id(
            request_id=_request().request_id,
            description="Restore previous version",
            target_ids=(target.target_id,),
        ),
        description="Restore previous version",
        target_ids=(target.target_id,),
    )


def _action(
    target: ChangeTarget,
    verification: VerificationStep,
    rollback: RollbackStep,
    *,
    destructive: bool = False,
    action_type: ChangeActionType = ChangeActionType.MODIFY,
) -> ChangeAction:
    return ChangeAction(
        action_id=change_action_id(
            request_id=_request().request_id,
            target_id=target.target_id,
            action_type=action_type.value,
            description="Modify target",
        ),
        target_id=target.target_id,
        action_type=action_type,
        description="Modify target",
        verification_step_ids=(verification.step_id,),
        rollback_step_ids=(rollback.step_id,),
        destructive=destructive,
        mutating=True,
    )


def test_change_request_id_is_deterministic() -> None:
    first = change_request_id(
        mission_id="mission",
        task_ids=("task-b", "task-a"),
        objective="Objective",
        constraints=("constraint-b", "constraint-a"),
        requested_outcomes=("outcome-b", "outcome-a"),
        source_fingerprints={"z": "2", "a": "1"},
    )
    second = change_request_id(
        mission_id="mission",
        task_ids=("task-a", "task-b"),
        objective="Objective",
        constraints=("constraint-a", "constraint-b"),
        requested_outcomes=("outcome-a", "outcome-b"),
        source_fingerprints={"a": "1", "z": "2"},
    )

    assert first == second


def test_change_request_id_changes_with_mission() -> None:
    first = change_request_id(
        mission_id="mission-a",
        task_ids=("task",),
        objective="Objective",
        constraints=(),
        requested_outcomes=(),
        source_fingerprints={},
    )
    second = change_request_id(
        mission_id="mission-b",
        task_ids=("task",),
        objective="Objective",
        constraints=(),
        requested_outcomes=(),
        source_fingerprints={},
    )

    assert first != second


def test_request_fingerprint_ignores_existing_value() -> None:
    request = _request()
    changed = request.model_copy(update={"request_fingerprint": "different"})

    assert change_request_fingerprint(request) == change_request_fingerprint(changed)


def test_target_id_is_deterministic() -> None:
    first = change_target_id(
        target_type="file",
        path="forge/example.py",
        component="example",
    )
    second = change_target_id(
        target_type="file",
        path="forge/example.py",
        component="example",
    )

    assert first == second


def test_target_id_changes_with_path() -> None:
    first = change_target_id(
        target_type="file",
        path="a.py",
        component="example",
    )
    second = change_target_id(
        target_type="file",
        path="b.py",
        component="example",
    )

    assert first != second


def test_action_id_changes_with_action_type() -> None:
    first = change_action_id(
        request_id="request",
        target_id="target",
        action_type="modify",
        description="Change target",
    )
    second = change_action_id(
        request_id="request",
        target_id="target",
        action_type="delete",
        description="Change target",
    )

    assert first != second


def test_dependency_id_is_deterministic() -> None:
    first = dependency_impact_id(
        source_target_id="source",
        affected_target_id="affected",
        dependency_type="direct",
        depth=1,
    )
    second = dependency_impact_id(
        source_target_id="source",
        affected_target_id="affected",
        dependency_type="direct",
        depth=1,
    )

    assert first == second


def test_risk_factor_id_sorts_source_ids() -> None:
    first = risk_factor_id(
        factor_type="security",
        reason="Security risk",
        source_ids=("b", "a"),
    )
    second = risk_factor_id(
        factor_type="security",
        reason="Security risk",
        source_ids=("a", "b"),
    )

    assert first == second


def test_verification_id_sorts_target_ids() -> None:
    first = verification_step_id(
        request_id="request",
        verification_type="unit_test",
        description="Run tests",
        target_ids=("b", "a"),
    )
    second = verification_step_id(
        request_id="request",
        verification_type="unit_test",
        description="Run tests",
        target_ids=("a", "b"),
    )

    assert first == second


def test_rollback_id_is_deterministic() -> None:
    first = rollback_step_id(
        request_id="request",
        description="Restore",
        target_ids=("target",),
    )
    second = rollback_step_id(
        request_id="request",
        description="Restore",
        target_ids=("target",),
    )

    assert first == second


def test_phase_id_changes_with_sequence() -> None:
    first = change_phase_id(
        request_id="request",
        phase_type="implementation",
        sequence=1,
        action_ids=("action",),
    )
    second = change_phase_id(
        request_id="request",
        phase_type="implementation",
        sequence=2,
        action_ids=("action",),
    )

    assert first != second


def test_component_fingerprints_are_repeatable() -> None:
    target = _target()
    verification = _verification(target)
    rollback = _rollback(target)
    action = _action(target, verification, rollback)
    dependency = DependencyImpact(
        dependency_id="dependency",
        source_target_id=target.target_id,
        affected_target_id=target.target_id,
        dependency_type=DependencyType.DIRECT,
        depth=1,
        reason="Dependency",
    )

    assert change_target_fingerprint(target) == change_target_fingerprint(target)
    assert change_action_fingerprint(action) == change_action_fingerprint(action)
    assert dependency_impact_fingerprint(dependency) == dependency_impact_fingerprint(dependency)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, RiskLevel.LOW),
        (29, RiskLevel.LOW),
        (30, RiskLevel.MEDIUM),
        (59, RiskLevel.MEDIUM),
        (60, RiskLevel.HIGH),
        (84, RiskLevel.HIGH),
        (85, RiskLevel.CRITICAL),
        (100, RiskLevel.CRITICAL),
    ],
)
def test_risk_level_for_score(
    score: int,
    expected: RiskLevel,
) -> None:
    assert risk_level_for_score(score) is expected


def test_risk_level_rejects_invalid_score() -> None:
    with pytest.raises(ChangePlanningRiskError):
        risk_level_for_score(101)


def test_medium_risk_requires_approval() -> None:
    configuration = ChangePlanningConfiguration()

    assert approval_required(
        RiskLevel.MEDIUM,
        configuration,
    )


def test_low_risk_approval_respects_configuration() -> None:
    default = ChangePlanningConfiguration()
    strict = ChangePlanningConfiguration(low_risk_approval_required=True)

    assert not approval_required(RiskLevel.LOW, default)
    assert approval_required(RiskLevel.LOW, strict)


def test_unknown_dependency_detection() -> None:
    dependency = DependencyImpact(
        dependency_id="dependency",
        source_target_id="source",
        affected_target_id="affected",
        dependency_type=DependencyType.UNKNOWN,
        depth=1,
        reason="Unknown",
        known=False,
    )

    assert unknown_dependency_present((dependency,))


def test_maximum_dependency_depth() -> None:
    dependencies = (
        DependencyImpact(
            dependency_id="a",
            source_target_id="source",
            affected_target_id="affected",
            dependency_type=DependencyType.DIRECT,
            depth=1,
            reason="Direct",
        ),
        DependencyImpact(
            dependency_id="b",
            source_target_id="source",
            affected_target_id="affected",
            dependency_type=DependencyType.TRANSITIVE,
            depth=4,
            reason="Transitive",
        ),
    )

    assert maximum_dependency_depth(dependencies) == 4


def test_destructive_action_detection() -> None:
    target = _target()
    verification = _verification(target)
    rollback = _rollback(target)
    action = _action(
        target,
        verification,
        rollback,
        destructive=True,
    )

    assert destructive_action_present((action,))


def test_mutating_action_count() -> None:
    target = _target()
    verification = _verification(target)
    rollback = _rollback(target)
    action = _action(target, verification, rollback)
    readonly = action.model_copy(
        update={
            "action_id": "readonly",
            "mutating": False,
        }
    )

    assert mutating_action_count((action, readonly)) == 1


def test_destructive_action_requires_rollback() -> None:
    target = _target()
    verification = _verification(target)
    rollback = _rollback(target)
    action = _action(
        target,
        verification,
        rollback,
        destructive=True,
    )

    assert requires_rollback(
        RiskLevel.LOW,
        (action,),
        ChangePlanningConfiguration(),
    )


def test_mutation_requires_verification() -> None:
    target = _target()
    verification = _verification(target)
    rollback = _rollback(target)
    action = _action(target, verification, rollback)

    assert requires_verification(
        (action,),
        ChangePlanningConfiguration(),
    )


def test_aggregate_risk_score_uses_highest_factor() -> None:
    factors = (
        RiskFactor(
            factor_id="a",
            factor_type=RiskFactorType.FILE_COUNT,
            score=20,
            reason="Files",
        ),
        RiskFactor(
            factor_id="b",
            factor_type=RiskFactorType.SECURITY,
            score=50,
            reason="Security",
            mitigation="Review security",
        ),
    )

    assert aggregate_risk_score(factors) >= 50


def test_build_risk_assessment_detects_database_scope() -> None:
    target = _target(
        target_type=ChangeTargetType.DATABASE,
        path="schema.sql",
        component="database",
    )
    verification = _verification(target)
    rollback = _rollback(target)
    action = _action(target, verification, rollback)

    assessment = build_risk_assessment(
        request_id=_request().request_id,
        targets=(target,),
        actions=(action,),
        dependencies=(),
        configuration=ChangePlanningConfiguration(),
    )

    assert assessment.risk_level in {
        RiskLevel.MEDIUM,
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    }
    assert assessment.approval_required


def test_unknown_dependency_policy_rejects_unknown() -> None:
    dependency = DependencyImpact(
        dependency_id="dependency",
        source_target_id="source",
        affected_target_id="affected",
        dependency_type=DependencyType.UNKNOWN,
        depth=1,
        reason="Unknown",
        known=False,
    )

    with pytest.raises(ChangePlanningRiskError):
        enforce_unknown_dependency_policy(
            (dependency,),
            ChangePlanningConfiguration(),
        )


def test_unknown_dependency_policy_can_allow_unknown() -> None:
    dependency = DependencyImpact(
        dependency_id="dependency",
        source_target_id="source",
        affected_target_id="affected",
        dependency_type=DependencyType.UNKNOWN,
        depth=1,
        reason="Unknown",
        known=False,
    )

    enforce_unknown_dependency_policy(
        (dependency,),
        ChangePlanningConfiguration(allow_unknown_dependencies=True),
    )


def test_risk_controls_require_verification() -> None:
    target = _target()
    verification = _verification(target)
    rollback = _rollback(target)
    action = _action(target, verification, rollback)
    assessment = ChangeRiskAssessment(
        assessment_id="assessment",
        risk_level=RiskLevel.MEDIUM,
        score=40,
        factors=(),
        approval_required=True,
        mitigations=(),
    )

    with pytest.raises(ChangePlanningRiskError):
        enforce_risk_controls(
            assessment,
            (action,),
            rollback_count=1,
            verification_count=0,
            configuration=ChangePlanningConfiguration(),
        )


def test_risk_controls_require_high_risk_rollback() -> None:
    target = _target()
    verification = _verification(target)
    rollback = _rollback(target)
    action = _action(target, verification, rollback)
    assessment = ChangeRiskAssessment(
        assessment_id="assessment",
        risk_level=RiskLevel.HIGH,
        score=70,
        factors=(),
        approval_required=True,
        mitigations=("Mitigation",),
    )

    with pytest.raises(ChangePlanningRiskError):
        enforce_risk_controls(
            assessment,
            (action,),
            rollback_count=0,
            verification_count=1,
            configuration=ChangePlanningConfiguration(),
        )


def test_plan_identity_and_fingerprint_are_repeatable() -> None:
    request = _request()
    target = _target()
    verification = _verification(target)
    rollback = _rollback(target)
    action = _action(target, verification, rollback)

    risk_factor = RiskFactor(
        factor_id="factor",
        factor_type=RiskFactorType.FILE_COUNT,
        score=10,
        reason="File count",
    )
    risk = ChangeRiskAssessment(
        assessment_id=risk_assessment_id(
            request_id=request.request_id,
            factors=(risk_factor,),
        ),
        risk_level=RiskLevel.LOW,
        score=10,
        factors=(risk_factor,),
        approval_required=False,
        mitigations=(),
    )
    phase = ChangePhase(
        phase_id=change_phase_id(
            request_id=request.request_id,
            phase_type=PlanningPhaseType.IMPLEMENTATION.value,
            sequence=1,
            action_ids=(action.action_id,),
        ),
        phase_type=PlanningPhaseType.IMPLEMENTATION,
        sequence=1,
        title="Implementation",
        action_ids=(action.action_id,),
    )

    plan_id = safe_change_plan_id(
        request=request,
        targets=(target,),
        actions=(action,),
        dependencies=(),
        risk_assessment=risk,
        verification_steps=(verification,),
        rollback_steps=(rollback,),
        phases=(phase,),
    )

    provisional = SafeChangePlan(
        plan_id=plan_id,
        plan_fingerprint="pending",
        request=request,
        targets=(target,),
        actions=(action,),
        dependencies=(),
        risk_assessment=risk,
        verification_steps=(verification,),
        rollback_steps=(rollback,),
        phases=(phase,),
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
            "mission": "a",
            "tasks": "b",
        },
    )

    first = safe_change_plan_fingerprint(provisional)
    second = safe_change_plan_fingerprint(
        provisional.model_copy(update={"plan_fingerprint": "different"})
    )

    assert first == second
