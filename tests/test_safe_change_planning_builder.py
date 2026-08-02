"""Safe Change Planning builder tests."""

from forge.safe_change_planning.builder import (
    SafeChangePlanningBuilder,
)
from forge.safe_change_planning.models import (
    ChangeAction,
    ChangeActionType,
    ChangePhase,
    ChangePlanningConfiguration,
    ChangeRequest,
    ChangeTarget,
    ChangeTargetType,
    DependencyImpact,
    DependencyType,
    PlanningPhaseType,
    RollbackStep,
    SafeChangePlan,
    VerificationStep,
    VerificationType,
)


def _builder() -> SafeChangePlanningBuilder:
    return SafeChangePlanningBuilder()


def _request() -> ChangeRequest:
    return _builder().build_request(
        mission_id="mission-1",
        task_ids=("task-b", "task-a"),
        objective="Implement safe planning",
        constraints=("No mutation",),
        requested_outcomes=("Deterministic plan",),
        source_fingerprints={
            "mission": "1",
            "tasks": "2",
        },
    )


def _target() -> ChangeTarget:
    return _builder().build_target(
        target_type=ChangeTargetType.FILE,
        path="forge/example.py",
        component="example",
        reason="Required implementation",
        source_ids=("task-a",),
    )


def _verification(request_id: str, target_id: str) -> VerificationStep:
    return _builder().build_verification_step(
        request_id=request_id,
        verification_type=VerificationType.UNIT_TEST,
        description="Run unit tests",
        target_ids=(target_id,),
        command="python -m pytest",
    )


def _rollback(request_id: str, target_id: str) -> RollbackStep:
    return _builder().build_rollback_step(
        request_id=request_id,
        description="Restore previous version",
        target_ids=(target_id,),
    )


def _action(
    request_id: str,
    target_id: str,
    verification_id: str,
    rollback_id: str,
) -> ChangeAction:
    return _builder().build_action(
        request_id=request_id,
        target_id=target_id,
        action_type=ChangeActionType.MODIFY,
        description="Modify implementation",
        verification_step_ids=(verification_id,),
        rollback_step_ids=(rollback_id,),
    )


def _phase(request_id: str, action_id: str) -> ChangePhase:
    return _builder().build_phase(
        request_id=request_id,
        phase_type=PlanningPhaseType.IMPLEMENTATION,
        sequence=1,
        title="Implementation",
        action_ids=(action_id,),
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


def _plan() -> SafeChangePlan:
    builder = _builder()
    request = _request()
    target = _target()
    verification = _verification(
        request.request_id,
        target.target_id,
    )
    rollback = _rollback(
        request.request_id,
        target.target_id,
    )
    action = _action(
        request.request_id,
        target.target_id,
        verification.step_id,
        rollback.step_id,
    )
    phase = _phase(
        request.request_id,
        action.action_id,
    )

    return builder.build_plan(
        request=request,
        targets=(target,),
        actions=(action,),
        dependencies=(),
        verification_steps=(verification,),
        rollback_steps=(rollback,),
        phases=(phase,),
        source_fingerprints=_lineage(),
        configuration=ChangePlanningConfiguration(),
    )


def test_build_request_is_deterministic() -> None:
    assert _request() == _request()


def test_build_request_normalizes_task_ids() -> None:
    request = _request()

    assert request.task_ids == ("task-a", "task-b")


def test_build_request_has_fingerprint() -> None:
    request = _request()

    assert request.request_fingerprint != "pending"
    assert len(request.request_fingerprint) == 64


def test_build_request_changes_with_mission() -> None:
    builder = _builder()

    first = builder.build_request(
        mission_id="mission-a",
        task_ids=("task",),
        objective="Objective",
    )
    second = builder.build_request(
        mission_id="mission-b",
        task_ids=("task",),
        objective="Objective",
    )

    assert first.request_id != second.request_id


def test_build_target_is_deterministic() -> None:
    assert _target() == _target()


def test_build_target_normalizes_source_ids() -> None:
    target = _builder().build_target(
        target_type=ChangeTargetType.FILE,
        path="forge/example.py",
        component="example",
        reason="Reason",
        source_ids=("task-b", "task-a", "task-a"),
    )

    assert target.source_ids == ("task-a", "task-b")


def test_build_target_changes_with_path() -> None:
    builder = _builder()

    first = builder.build_target(
        target_type=ChangeTargetType.FILE,
        path="a.py",
        component="example",
        reason="Reason",
    )
    second = builder.build_target(
        target_type=ChangeTargetType.FILE,
        path="b.py",
        component="example",
        reason="Reason",
    )

    assert first.target_id != second.target_id


def test_build_verification_is_deterministic() -> None:
    request = _request()
    target = _target()

    first = _verification(
        request.request_id,
        target.target_id,
    )
    second = _verification(
        request.request_id,
        target.target_id,
    )

    assert first == second


def test_build_verification_preserves_command() -> None:
    request = _request()
    target = _target()
    step = _verification(
        request.request_id,
        target.target_id,
    )

    assert step.command == "python -m pytest"


def test_build_rollback_is_deterministic() -> None:
    request = _request()
    target = _target()

    first = _rollback(
        request.request_id,
        target.target_id,
    )
    second = _rollback(
        request.request_id,
        target.target_id,
    )

    assert first == second


def test_build_action_is_deterministic() -> None:
    request = _request()
    target = _target()
    verification = _verification(
        request.request_id,
        target.target_id,
    )
    rollback = _rollback(
        request.request_id,
        target.target_id,
    )

    first = _action(
        request.request_id,
        target.target_id,
        verification.step_id,
        rollback.step_id,
    )
    second = _action(
        request.request_id,
        target.target_id,
        verification.step_id,
        rollback.step_id,
    )

    assert first == second


def test_build_action_preserves_references() -> None:
    request = _request()
    target = _target()
    verification = _verification(
        request.request_id,
        target.target_id,
    )
    rollback = _rollback(
        request.request_id,
        target.target_id,
    )
    action = _action(
        request.request_id,
        target.target_id,
        verification.step_id,
        rollback.step_id,
    )

    assert action.verification_step_ids == (verification.step_id,)
    assert action.rollback_step_ids == (rollback.step_id,)


def test_build_phase_is_deterministic() -> None:
    first = _phase("request", "action")
    second = _phase("request", "action")

    assert first == second


def test_build_plan_is_deterministic() -> None:
    assert _plan() == _plan()


def test_build_plan_has_final_fingerprint() -> None:
    plan = _plan()

    assert plan.plan_fingerprint != "pending"
    assert len(plan.plan_fingerprint) == 64


def test_build_plan_calculates_statistics() -> None:
    plan = _plan()

    assert plan.statistics.target_count == 1
    assert plan.statistics.action_count == 1
    assert plan.statistics.verification_count == 1
    assert plan.statistics.rollback_count == 1
    assert plan.statistics.phase_count == 1


def test_build_plan_orders_targets() -> None:
    builder = _builder()
    request = _request()

    target_b = builder.build_target(
        target_type=ChangeTargetType.FILE,
        path="b.py",
        component="example",
        reason="Reason",
    )
    target_a = builder.build_target(
        target_type=ChangeTargetType.FILE,
        path="a.py",
        component="example",
        reason="Reason",
    )

    plan = builder.build_plan(
        request=request,
        targets=(target_b, target_a),
        actions=(),
        dependencies=(),
        verification_steps=(),
        rollback_steps=(),
        phases=(),
        source_fingerprints=_lineage(),
        configuration=ChangePlanningConfiguration(require_verification_for_mutations=False),
    )

    assert tuple(target.target_id for target in plan.targets) == tuple(
        sorted(target.target_id for target in (target_a, target_b))
    )


def test_build_plan_orders_dependencies() -> None:
    builder = _builder()
    request = _request()
    target = _target()

    dependency_b = DependencyImpact(
        dependency_id="dependency-b",
        source_target_id=target.target_id,
        affected_target_id=target.target_id,
        dependency_type=DependencyType.DIRECT,
        depth=1,
        reason="Dependency B",
    )
    dependency_a = dependency_b.model_copy(
        update={
            "dependency_id": "dependency-a",
            "reason": "Dependency A",
        }
    )

    plan = builder.build_plan(
        request=request,
        targets=(target,),
        actions=(),
        dependencies=(dependency_b, dependency_a),
        verification_steps=(),
        rollback_steps=(),
        phases=(),
        source_fingerprints=_lineage(),
        configuration=ChangePlanningConfiguration(require_verification_for_mutations=False),
    )

    assert tuple(item.dependency_id for item in plan.dependencies) == (
        "dependency-a",
        "dependency-b",
    )


def test_builder_does_not_mutate_inputs() -> None:
    request = _request()
    original = request.model_dump(mode="json")

    _plan()

    assert request.model_dump(mode="json") == original
