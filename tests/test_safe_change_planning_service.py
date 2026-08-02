"""Safe Change Planning service tests."""

from pathlib import Path

import pytest

from forge.safe_change_planning.builder import (
    SafeChangePlanningBuilder,
)
from forge.safe_change_planning.errors import (
    ChangePlanningConfigurationError,
    ChangePlanningPersistenceError,
    ChangePlanningValidationError,
    ChangePlanNotFoundError,
)
from forge.safe_change_planning.models import (
    ChangeAction,
    ChangeActionType,
    ChangePhase,
    ChangePlanningConfiguration,
    ChangeRequest,
    ChangeTarget,
    ChangeTargetType,
    PlanningPhaseType,
    RollbackStep,
    SafeChangePlan,
    VerificationStep,
    VerificationType,
)
from forge.safe_change_planning.renderer import (
    SAFE_CHANGE_REPORT_NAMES,
)
from forge.safe_change_planning.service import (
    SAFE_CHANGE_MEMORY_FILE,
    SAFE_CHANGE_REQUEST_FILE,
    SafeChangePlanningService,
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


def _artifacts() -> tuple[
    ChangeRequest,
    ChangeTarget,
    VerificationStep,
    RollbackStep,
    ChangeAction,
    ChangePhase,
]:
    builder = SafeChangePlanningBuilder()
    request = builder.build_request(
        mission_id="mission-1",
        task_ids=("task-1",),
        objective="Implement safe change",
        source_fingerprints={
            "mission": "1",
            "tasks": "2",
        },
    )
    target = builder.build_target(
        target_type=ChangeTargetType.FILE,
        path="forge/example.py",
        component="example",
        reason="Required implementation",
        source_ids=("task-1",),
    )
    verification = builder.build_verification_step(
        request_id=request.request_id,
        verification_type=VerificationType.UNIT_TEST,
        description="Run unit tests",
        target_ids=(target.target_id,),
    )
    rollback = builder.build_rollback_step(
        request_id=request.request_id,
        description="Restore previous version",
        target_ids=(target.target_id,),
    )
    action = builder.build_action(
        request_id=request.request_id,
        target_id=target.target_id,
        action_type=ChangeActionType.MODIFY,
        description="Modify implementation",
        verification_step_ids=(verification.step_id,),
        rollback_step_ids=(rollback.step_id,),
    )
    phase = builder.build_phase(
        request_id=request.request_id,
        phase_type=PlanningPhaseType.IMPLEMENTATION,
        sequence=1,
        title="Implementation",
        action_ids=(action.action_id,),
    )

    return (
        request,
        target,
        verification,
        rollback,
        action,
        phase,
    )


def _service() -> SafeChangePlanningService:
    return SafeChangePlanningService()


def _plan() -> SafeChangePlan:
    (
        request,
        target,
        verification,
        rollback,
        action,
        phase,
    ) = _artifacts()

    return _service().create_plan(
        request=request,
        targets=(target,),
        actions=(action,),
        dependencies=(),
        verification_steps=(verification,),
        rollback_steps=(rollback,),
        phases=(phase,),
        source_fingerprints=_lineage(),
    )


def test_create_request_is_deterministic() -> None:
    service = _service()

    first = service.create_request(
        mission_id="mission",
        task_ids=("task",),
        objective="Objective",
    )
    second = service.create_request(
        mission_id="mission",
        task_ids=("task",),
        objective="Objective",
    )

    assert first == second


def test_create_request_rejects_disabled_service() -> None:
    service = SafeChangePlanningService(ChangePlanningConfiguration(enabled=False))

    with pytest.raises(ChangePlanningConfigurationError):
        service.create_request(
            mission_id="mission",
            task_ids=("task",),
            objective="Objective",
        )


def test_validate_request_accepts_matching_lineage() -> None:
    service = _service()
    request = service.create_request(
        mission_id="mission",
        task_ids=("task",),
        objective="Objective",
        source_fingerprints={"mission": "1"},
    )

    result = service.validate_request(
        request,
        known_mission_id="mission",
        known_task_ids=("task",),
        required_source_fingerprints={"mission": "1"},
    )

    assert result.valid


def test_validate_request_rejects_mismatch() -> None:
    service = _service()
    request = service.create_request(
        mission_id="mission-a",
        task_ids=("task",),
        objective="Objective",
    )

    result = service.validate_request(
        request,
        known_mission_id="mission-b",
        known_task_ids=("task",),
        required_source_fingerprints={},
    )

    assert not result.valid


def test_validate_request_or_raise_raises() -> None:
    service = _service()
    request = service.create_request(
        mission_id="mission-a",
        task_ids=("task",),
        objective="Objective",
    )

    with pytest.raises(ChangePlanningValidationError):
        service.validate_request_or_raise(
            request,
            known_mission_id="mission-b",
            known_task_ids=("task",),
            required_source_fingerprints={},
        )


def test_create_plan_returns_valid_plan() -> None:
    plan = _plan()

    assert _service().validate_plan(plan).valid


def test_create_plan_is_deterministic() -> None:
    assert _plan() == _plan()


def test_validate_plan_or_raise_returns_result() -> None:
    result = _service().validate_plan_or_raise(_plan())

    assert result.valid


def test_render_reports_returns_complete_suite() -> None:
    reports = _service().render_reports(_plan())

    assert set(reports) == set(SAFE_CHANGE_REPORT_NAMES)


def test_write_reports_creates_files(
    tmp_path: Path,
) -> None:
    written = _service().write_reports(
        _plan(),
        tmp_path,
    )

    assert set(written) == set(SAFE_CHANGE_REPORT_NAMES)


def test_save_request_creates_file(
    tmp_path: Path,
) -> None:
    request = _artifacts()[0]

    path = _service().save_request(
        request,
        tmp_path,
    )

    assert path == tmp_path / SAFE_CHANGE_REQUEST_FILE
    assert path.is_file()


def test_load_request_round_trip(
    tmp_path: Path,
) -> None:
    service = _service()
    request = _artifacts()[0]

    service.save_request(request, tmp_path)

    assert service.load_request(tmp_path) == request


def test_load_missing_request_raises(
    tmp_path: Path,
) -> None:
    with pytest.raises(ChangePlanNotFoundError):
        _service().load_request(tmp_path)


def test_load_corrupt_request_raises(
    tmp_path: Path,
) -> None:
    path = tmp_path / SAFE_CHANGE_REQUEST_FILE
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ChangePlanningPersistenceError):
        _service().load_request(tmp_path)


def test_save_plan_creates_file(
    tmp_path: Path,
) -> None:
    path = _service().save_plan(
        _plan(),
        tmp_path,
    )

    assert path == tmp_path / SAFE_CHANGE_MEMORY_FILE
    assert path.is_file()


def test_load_plan_round_trip(
    tmp_path: Path,
) -> None:
    service = _service()
    plan = _plan()

    service.save_plan(plan, tmp_path)

    assert service.load_plan(tmp_path) == plan


def test_load_missing_plan_raises(
    tmp_path: Path,
) -> None:
    with pytest.raises(ChangePlanNotFoundError):
        _service().load_plan(tmp_path)


def test_load_corrupt_plan_raises(
    tmp_path: Path,
) -> None:
    path = tmp_path / SAFE_CHANGE_MEMORY_FILE
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ChangePlanningPersistenceError):
        _service().load_plan(tmp_path)


def test_build_persist_and_report(
    tmp_path: Path,
) -> None:
    memory = tmp_path / "memory"
    reports = tmp_path / "reports"

    (
        request,
        target,
        verification,
        rollback,
        action,
        phase,
    ) = _artifacts()

    plan = _service().build_persist_and_report(
        request=request,
        targets=(target,),
        actions=(action,),
        dependencies=(),
        verification_steps=(verification,),
        rollback_steps=(rollback,),
        phases=(phase,),
        source_fingerprints=_lineage(),
        memory_path=memory,
        reports_path=reports,
    )

    assert (memory / SAFE_CHANGE_REQUEST_FILE).is_file()
    assert (memory / SAFE_CHANGE_MEMORY_FILE).is_file()
    assert plan.plan_id


def test_build_persist_and_report_creates_reports(
    tmp_path: Path,
) -> None:
    memory = tmp_path / "memory"
    reports = tmp_path / "reports"

    (
        request,
        target,
        verification,
        rollback,
        action,
        phase,
    ) = _artifacts()

    _service().build_persist_and_report(
        request=request,
        targets=(target,),
        actions=(action,),
        dependencies=(),
        verification_steps=(verification,),
        rollback_steps=(rollback,),
        phases=(phase,),
        source_fingerprints=_lineage(),
        memory_path=memory,
        reports_path=reports,
    )

    for name in SAFE_CHANGE_REPORT_NAMES:
        assert (reports / name).is_file()


def test_service_uses_injected_builder() -> None:
    builder = SafeChangePlanningBuilder()
    service = SafeChangePlanningService(builder=builder)

    assert service.builder is builder


def test_service_uses_safe_default_configuration() -> None:
    service = _service()

    assert service.configuration.enabled
    assert service.configuration.strict_validation


def test_service_does_not_mutate_request() -> None:
    request = _artifacts()[0]
    original = request.model_dump(mode="json")

    _plan()

    assert request.model_dump(mode="json") == original


def test_saved_plan_has_no_temporary_file(
    tmp_path: Path,
) -> None:
    _service().save_plan(_plan(), tmp_path)

    assert not tuple(tmp_path.glob("*.tmp"))


def test_saved_request_has_no_temporary_file(
    tmp_path: Path,
) -> None:
    _service().save_request(
        _artifacts()[0],
        tmp_path,
    )

    assert not tuple(tmp_path.glob("*.tmp"))
